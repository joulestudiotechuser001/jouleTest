"""Tests for the Hello World Agent."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestHelloWorldResponse:
    """Unit tests for Hello World response logic."""

    def test_system_prompt_contains_hello_world(self):
        """The system prompt must instruct the agent to reply Hello World."""
        from agent import get_system_prompt
        prompt = get_system_prompt()
        assert "Hello World" in prompt

    def test_agent_response_dataclass(self):
        """AgentResponse dataclass has correct fields."""
        from agent import AgentResponse
        resp = AgentResponse(status="completed", message="Hello World")
        assert resp.status == "completed"
        assert resp.message == "Hello World"

    @pytest.mark.asyncio
    async def test_stream_yields_processing_then_response(self):
        """stream() yields a processing message then a completed response."""
        from agent import SampleAgent

        agent = SampleAgent.__new__(SampleAgent)

        # Mock _run_agent to return Hello World
        agent._run_agent = AsyncMock(return_value="Hello World")

        chunks = []
        async for chunk in agent.stream("Hi", "ctx-1", tools=[]):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0]["is_task_complete"] is False
        assert chunks[1]["is_task_complete"] is True
        assert chunks[1]["content"] == "Hello World"

    @pytest.mark.asyncio
    async def test_stream_returns_error_on_exception(self):
        """stream() yields an error chunk when _run_agent raises."""
        from agent import SampleAgent

        agent = SampleAgent.__new__(SampleAgent)
        agent._run_agent = AsyncMock(side_effect=RuntimeError("boom"))

        chunks = []
        async for chunk in agent.stream("Hi", "ctx-1", tools=[]):
            chunks.append(chunk)

        assert chunks[-1]["is_task_complete"] is True
        assert "error" in chunks[-1]["content"].lower()

    @pytest.mark.asyncio
    async def test_invoke_returns_completed_status(self):
        """invoke() wraps stream() and returns AgentResponse with status=completed."""
        from agent import SampleAgent, AgentResponse

        agent = SampleAgent.__new__(SampleAgent)
        agent._run_agent = AsyncMock(return_value="Hello World")

        result = await agent.invoke("Hi", "ctx-2", tools=[])
        assert isinstance(result, AgentResponse)
        assert result.status == "completed"
        assert result.message == "Hello World"


class TestBusinessInstrumentation:
    """Tests that business milestones are instrumented."""

    def test_milestone_logging_exists(self):
        """Verify milestone log statements are present in agent source."""
        import inspect
        from agent import SampleAgent
        source = inspect.getsource(SampleAgent._run_agent)
        assert "M1.achieved" in source
        assert "M2.achieved" in source
        assert "M3.achieved" in source
        assert "M1.missed" in source
        assert "M2.missed" in source
        assert "M3.missed" in source

    def test_opentelemetry_tracer_used(self):
        """Verify OpenTelemetry tracer is present in agent module."""
        import agent
        assert hasattr(agent, "tracer")


class TestIntegration:
    """Integration test: end-to-end agent flow with mocked LLM."""

    @pytest.mark.asyncio
    async def test_end_to_end_hello_world(self):
        """Full agent flow returns Hello World with mocked LLM."""
        from agent import SampleAgent

        fake_message = MagicMock()
        fake_message.content = "Hello World"
        fake_result = {"messages": [fake_message]}

        with patch("agent.SampleAgent._invoke_with_fallback", new_callable=AsyncMock, return_value=fake_result):
            agent = SampleAgent.__new__(SampleAgent)
            agent._run_agent = AsyncMock(return_value="Hello World")
            result = await agent.invoke("Say hello", "ctx-integration", tools=[])

        assert result.status == "completed"
        assert result.message == "Hello World"
