"""Unit and integration tests for the Hello World Agent."""

from __future__ import annotations

import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure app/ is on the path
APP_DIR = Path(__file__).parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


# ---------------------------------------------------------------------------
# Unit test: agent always responds with "Hello World"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_returns_hello_world():
    """Unit test: verify agent returns Hello World for any input."""
    from agent import SampleAgent

    agent = SampleAgent.__new__(SampleAgent)
    agent._primary_model = "mock-model"
    agent._fallback_model = ""
    agent._fallback_llm = None
    agent._temperature = 0.0
    agent._checkpointer = None
    agent._summarization_middleware = None

    mock_result = {"messages": [MagicMock(content="Hello World")]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=mock_result)):
        with patch.object(agent, "_create_graph", return_value=MagicMock()):
            response = await agent._run_agent("hi", "ctx-1", tools=[])

    assert response == "Hello World"


# ---------------------------------------------------------------------------
# Integration test: end-to-end agent invocation with mocked LLM
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_integration_hello_world():
    """Integration test: end-to-end flow returns Hello World."""
    from agent import SampleAgent

    agent = SampleAgent.__new__(SampleAgent)
    agent._primary_model = "mock-model"
    agent._fallback_model = ""
    agent._fallback_llm = None
    agent._temperature = 0.0
    agent._checkpointer = None
    agent._summarization_middleware = None

    mock_result = {"messages": [MagicMock(content="Hello World")]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=mock_result)):
        result = await agent.invoke("hello", "ctx-2", tools=[])

    assert result.status == "completed"
    assert result.message == "Hello World"


# ---------------------------------------------------------------------------
# Unit test: stream yields Hello World
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_stream_hello_world():
    """Unit test: stream method yields final Hello World response."""
    from agent import SampleAgent

    agent = SampleAgent.__new__(SampleAgent)
    agent._primary_model = "mock-model"
    agent._fallback_model = ""
    agent._fallback_llm = None
    agent._temperature = 0.0
    agent._checkpointer = None
    agent._summarization_middleware = None

    mock_result = {"messages": [MagicMock(content="Hello World")]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=mock_result)):
        chunks = []
        async for chunk in agent.stream("test", "ctx-3", tools=[]):
            chunks.append(chunk)

    assert any(c.get("is_task_complete") and c.get("content") == "Hello World" for c in chunks)


# ---------------------------------------------------------------------------
# Unit test: instrumentation milestone logging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_milestone_logging(caplog):
    """Unit test: verify M1/M2/M3 milestone log statements are emitted."""
    import logging
    from agent import SampleAgent

    agent = SampleAgent.__new__(SampleAgent)
    agent._primary_model = "mock-model"
    agent._fallback_model = ""
    agent._fallback_llm = None
    agent._temperature = 0.0
    agent._checkpointer = None
    agent._summarization_middleware = None

    mock_result = {"messages": [MagicMock(content="Hello World")]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=mock_result)):
        with caplog.at_level(logging.INFO, logger="agent"):
            chunks = [c async for c in agent.stream("hello", "ctx-4", tools=[])]

    log_messages = caplog.text
    assert "M1.achieved" in log_messages
    assert "M2.achieved" in log_messages
    assert "M3.achieved" in log_messages
