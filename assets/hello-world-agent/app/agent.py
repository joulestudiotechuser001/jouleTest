import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Literal, Sequence
from opentelemetry import trace

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langgraph.graph.state import CompiledStateGraph
from litellm.exceptions import APIConnectionError, APIError, Timeout
from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section
from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer
from mcp_providers.agw import get_user_sub

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return "sap/anthropic--claude-4.5-sonnet"


@agent_model(
    key="config.fallback_model",
    label="Fallback LLM Model",
    description="Fallback model used when the primary model is unavailable. Leave empty to disable fallback.",
)
def get_fallback_model_name() -> str:
    return ""


@agent_config(
    key="config.temperature",
    label="LLM Temperature",
    description="Controls randomness of responses (0.0 = deterministic, 1.0 = creative)",
)
def get_temperature() -> float:
    return 0.0

@agent_config(
    key="config.checkpointer.ttl_seconds",
    label="Thread TTL (seconds)",
    description="Evict inactive conversation threads after this period of "
                "inactivity. Set to 0 to disable eviction.",
)
def thread_ttl_seconds() -> int:
    return 3600 # 1 hour

SUMMARIZATION_TRIGGER_TOKENS = 30_000
SUMMARIZATION_MODEL = "sap/anthropic--claude-4.5-haiku"

@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The full system prompt defining the agent's role and behavior",
    validation={"format": "markdown", "max_length": 5000},
)
def get_system_prompt() -> str:
    return """You always respond with exactly 'Hello World', regardless of what the user says. Do not add any other text."""


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


class SampleAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        ttl = thread_ttl_seconds()
        self._primary_model = get_model_name()
        self._fallback_model = get_fallback_model_name().strip()
        self._temperature = get_temperature()

        # cache_control_injection_points is picked up by litellm's AnthropicCacheControlHook,
        # which injects a cache breakpoint on the system message before every API call.
        # This caches the static prefix (system prompt + tool schemas) at 0.1× input cost
        # on cache-hit turns. No beta header required as of current litellm/Anthropic versions.
        _cache_kwargs = {
            "cache_control_injection_points": [
                {"location": "message", "role": "system", "control": {"type": "ephemeral"}}
            ]
        }
        self.llm = ChatLiteLLM(
            model=self._primary_model,
            temperature=self._temperature,
            model_kwargs=_cache_kwargs,
        )
        self._fallback_llm = (
            ChatLiteLLM(
                model=self._fallback_model,
                temperature=self._temperature,
                model_kwargs=_cache_kwargs,
            )
            if self._fallback_model
            else None
        )
        self._checkpointer = create_checkpointer(ttl_seconds=ttl or None)
        # Summarization compresses history once it exceeds the token trigger, keeping only
        # the last N messages in full. This intentionally invalidates the prompt cache when
        # it fires (the summarized history is new content), but the static prefix —
        # system prompt + tool schemas, marked cacheable via cache_control_injection_points
        # on self.llm — stays cacheable across all turns, summarized or not.
        summarization_llm = ChatLiteLLM(
            model=SUMMARIZATION_MODEL, temperature=0.0
        )
        self._summarization_middleware = SummarizationMiddleware(
            model=summarization_llm,
            trigger=("tokens", SUMMARIZATION_TRIGGER_TOKENS),
            keep=("messages", 4),
        )

    def _create_graph(
        self,
        llm: ChatLiteLLM,
        tools: Sequence[BaseTool],
        system_prompt: str,
    ) -> CompiledStateGraph:
        """Create a LangGraph agent with the specified LLM."""
        return create_agent(
            llm,
            tools=list(tools),
            system_prompt=system_prompt,
            checkpointer=self._checkpointer,
            middleware=[self._summarization_middleware],
        )

    async def _invoke_with_fallback(
        self,
        tools: Sequence[BaseTool],
        system_prompt: str,
        query: str,
        context_id: str,
        extra_messages: list | None = None,
    ) -> dict[str, Any]:
        """Invoke the agent and fall back only for transient LLM failures."""
        config = {"configurable": {"thread_id": f"{get_user_sub()}:{context_id}"}}
        messages = {"messages": (extra_messages or []) + [HumanMessage(content=query)]}

        try:
            graph = self._create_graph(self.llm, tools, system_prompt)
            return await graph.ainvoke(messages, config)
        except (APIConnectionError, APIError, Timeout) as primary_error:
            if not self._fallback_llm:
                raise

            logger.warning(
                "Primary model '%s' failed. Retrying with fallback model '%s'. Error: %s",
                self._primary_model,
                self._fallback_model,
                primary_error,
            )

        graph = self._create_graph(self._fallback_llm, tools, system_prompt)
        result = await graph.ainvoke(messages, config)
        logger.info(
            "Request completed with fallback model '%s' after primary model '%s' failed.",
            self._fallback_model,
            self._primary_model,
        )
        return result

    async def _run_agent(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool],
    ) -> str:
        """Core agent logic with business step instrumentation.

        Returns the agent's response string.
        """
        # M1: Agent receives message
        with tracer.start_as_current_span("M1.agent_receives_message"):
            if query:
                logger.info("M1.achieved: agent received incoming message")
            else:
                logger.warning("M1.missed: no message received or handler not invoked")

        # M2: Agent processes request
        with tracer.start_as_current_span("M2.agent_processes_request"):
            try:
                system_prompt = get_system_prompt()
                tool_names = [tool.name for tool in tools]
                logger.info("Running agent with %d tool(s): %s", len(tool_names), tool_names)

                extra: list = []
                if not tools:
                    extra.append(
                        SystemMessage(
                            content="IMPORTANT: No tools are currently available. "
                            "Do not attempt to call any tools. Respond to the user "
                            "explaining that tools are temporarily unavailable."
                        )
                    )

                result = await self._invoke_with_fallback(
                    tools=tools,
                    system_prompt=system_prompt,
                    query=query,
                    context_id=context_id,
                    extra_messages=extra or None,
                )
                logger.info("M2.achieved: agent processed request successfully")
            except Exception:
                logger.warning("M2.missed: agent failed to process request")
                raise

        # M3: Agent replies Hello World
        with tracer.start_as_current_span("M3.agent_replies"):
            response = result["messages"][-1].content
            if "Hello World" in response:
                logger.info("M3.achieved: agent replied with Hello World")
            else:
                logger.warning("M3.missed: agent did not reply with Hello World")

        return response

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream agent responses.

        Args:
            query: User query to process
            context_id: Context identifier for the conversation
            tools: Optional sequence of LangChain tools. If None or empty, agent runs without tools.

        Yields:
            Status updates and final response with structure:
            - is_task_complete: Whether the task is complete
            - require_user_input: Whether user input is needed
            - content: The response content or status message
        """
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Processing...",
        }

        try:
            response = await self._run_agent(query, context_id, tools or [])
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response,
            }

        except Exception:
            logger.exception("Agent stream() failed")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": "I encountered an error while processing your request. Please try again.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AgentResponse:
        """Invoke agent and return final response.

        Args:
            query: User query to process
            context_id: Context identifier for the conversation
            tools: Optional sequence of LangChain tools. If None or empty, agent runs without tools.

        Returns:
            AgentResponse with status and message
        """
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(
            status="error", message=last.get("content", "Unknown error")
        )
