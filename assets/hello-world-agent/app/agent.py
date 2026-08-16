import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Literal, Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langgraph.graph.state import CompiledStateGraph
from litellm.exceptions import APIConnectionError, APIError, Timeout
from opentelemetry import trace
from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section
try:
    from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer
except ImportError:
    def create_checkpointer(**kwargs):
        return None

from mcp_tools import get_user_sub

tracer = trace.get_tracer(__name__)

logger = logging.getLogger(__name__)


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

@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The full system prompt defining the agent's role and behavior",
    validation={"format": "markdown", "max_length": 5000},
)
def get_system_prompt() -> str:
    return """You always respond with exactly 'Hello World' regardless of any input. Do not add any other text."""


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

        self.llm = ChatLiteLLM(model=self._primary_model, temperature=self._temperature)
        self._fallback_llm = (
            ChatLiteLLM(model=self._fallback_model, temperature=self._temperature)
            if self._fallback_model
            else None
        )

        self._checkpointer = create_checkpointer(ttl_seconds=ttl or None)
        self._summarization_middleware = SummarizationMiddleware(
            model=self.llm,
            trigger=("tokens", 100_000),
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
    ) -> dict[str, Any]:
        """Invoke the agent and fall back only for transient LLM failures."""
        config = {"configurable": {"thread_id": f"{get_user_sub()}:{context_id}"}}
        messages = {"messages": [HumanMessage(content=query)]}

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

    @tracer.start_as_current_span("m1-agent-invoked")
    async def _run_agent(self, query: str) -> str:
        """Core Hello World logic with M1 and M2 milestone instrumentation."""
        # M1 – Agent Invoked
        if not query and query != "":
            logger.warning("M1.missed: agent did not receive or parse the incoming request")
            return "Hello World"

        logger.info("M1.achieved: agent received incoming request")

        try:
            # M2 – Response Generated
            response = "Hello World"
            logger.info("M2.achieved: Hello World response generated successfully")
            return response
        except Exception:
            logger.exception("M2.missed: response generation step did not complete")
            raise

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
            response = await self._run_agent(query)

            # M3 – Response Delivered
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response,
            }
            logger.info("M3.achieved: Hello World response delivered to caller")

        except Exception:
            logger.exception("M3.missed: response delivery did not complete")
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
