"""Tests for Hello World agent."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_run_agent_returns_hello_world():
    """Unit test: _run_agent always returns 'Hello World'."""
    with patch("agent.trace") as mock_trace:
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_trace.get_tracer.return_value = mock_tracer

        from agent import SampleAgent
        agent = SampleAgent()
        result = await agent._run_agent("any message", "ctx-1")
        assert result == "Hello World"


@pytest.mark.asyncio
async def test_run_agent_returns_hello_world_for_empty_input():
    """Unit test: _run_agent returns 'Hello World' even for empty input."""
    with patch("agent.trace") as mock_trace:
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_trace.get_tracer.return_value = mock_tracer

        from agent import SampleAgent
        agent = SampleAgent()
        result = await agent._run_agent("", "ctx-2")
        assert result == "Hello World"


@pytest.mark.asyncio
async def test_stream_yields_hello_world():
    """Integration test: stream() yields 'Hello World' as final response."""
    with patch("agent.trace") as mock_trace:
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_trace.get_tracer.return_value = mock_tracer

        from agent import SampleAgent
        agent = SampleAgent()

        chunks = []
        async for chunk in agent.stream("hello", "ctx-3"):
            chunks.append(chunk)

        assert len(chunks) >= 1
        final = chunks[-1]
        assert final["is_task_complete"] is True
        assert final["content"] == "Hello World"


@pytest.mark.asyncio
async def test_invoke_returns_hello_world():
    """Integration test: invoke() returns AgentResponse with 'Hello World'."""
    with patch("agent.trace") as mock_trace:
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_trace.get_tracer.return_value = mock_tracer

        from agent import SampleAgent
        agent = SampleAgent()
        response = await agent.invoke("say hello", "ctx-4")
        assert response.status == "completed"
        assert response.message == "Hello World"
