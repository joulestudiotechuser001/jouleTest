"""Tests for the Hello World Agent."""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure app/ is on sys.path
APP_DIR = Path(__file__).parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_returns_hello_world(add_agent_to_path):
    """Unit test: agent invoke() always returns 'Hello World'."""
    from agent import SampleAgent

    with patch("agent.ChatLiteLLM") as mock_llm_cls, \
         patch("agent.create_checkpointer") as mock_checkpointer, \
         patch("agent.create_agent") as mock_create_agent, \
         patch("agent.SummarizationMiddleware"):

        # Setup mock LLM and graph
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm

        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [MagicMock(content="Hello World")]
        }
        mock_create_agent.return_value = mock_graph
        mock_checkpointer.return_value = MagicMock()

        agent = SampleAgent()
        result = await agent.invoke("Say something", "test-ctx-1")

        assert result.status == "completed"
        assert "Hello World" in result.message


@pytest.mark.asyncio
async def test_agent_stream_yields_hello_world(add_agent_to_path):
    """Unit test: agent stream() yields a completed response with Hello World."""
    from agent import SampleAgent

    with patch("agent.ChatLiteLLM") as mock_llm_cls, \
         patch("agent.create_checkpointer") as mock_checkpointer, \
         patch("agent.create_agent") as mock_create_agent, \
         patch("agent.SummarizationMiddleware"):

        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm

        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [MagicMock(content="Hello World")]
        }
        mock_create_agent.return_value = mock_graph
        mock_checkpointer.return_value = MagicMock()

        agent = SampleAgent()
        chunks = []
        async for chunk in agent.stream("hi", "test-ctx-2"):
            chunks.append(chunk)

        # Last chunk should be complete with Hello World
        final = chunks[-1]
        assert final["is_task_complete"] is True
        assert "Hello World" in final["content"]


@pytest.mark.asyncio
async def test_agent_handles_empty_query(add_agent_to_path):
    """Unit test: agent stream() handles empty/None query gracefully."""
    from agent import SampleAgent

    with patch("agent.ChatLiteLLM"), \
         patch("agent.create_checkpointer"), \
         patch("agent.create_agent"), \
         patch("agent.SummarizationMiddleware"):

        agent = SampleAgent()
        chunks = []
        async for chunk in agent.stream("", "test-ctx-3"):
            chunks.append(chunk)

        final = chunks[-1]
        assert final["is_task_complete"] is True


@pytest.mark.asyncio
async def test_agent_milestone_m1_logged(add_agent_to_path, caplog):
    """Unit test: M1 milestone is logged when message is received."""
    import logging
    from agent import SampleAgent

    with patch("agent.ChatLiteLLM") as mock_llm_cls, \
         patch("agent.create_checkpointer") as mock_checkpointer, \
         patch("agent.create_agent") as mock_create_agent, \
         patch("agent.SummarizationMiddleware"):

        mock_llm_cls.return_value = MagicMock()
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [MagicMock(content="Hello World")]
        }
        mock_create_agent.return_value = mock_graph
        mock_checkpointer.return_value = MagicMock()

        agent = SampleAgent()
        with caplog.at_level(logging.INFO, logger="agent"):
            await agent.invoke("hello", "test-ctx-m1")

        assert any("M1.achieved" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_agent_milestone_m2_logged(add_agent_to_path, caplog):
    """Unit test: M2 milestone is logged when response is generated."""
    import logging
    from agent import SampleAgent

    with patch("agent.ChatLiteLLM") as mock_llm_cls, \
         patch("agent.create_checkpointer") as mock_checkpointer, \
         patch("agent.create_agent") as mock_create_agent, \
         patch("agent.SummarizationMiddleware"):

        mock_llm_cls.return_value = MagicMock()
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [MagicMock(content="Hello World")]
        }
        mock_create_agent.return_value = mock_graph
        mock_checkpointer.return_value = MagicMock()

        agent = SampleAgent()
        with caplog.at_level(logging.INFO, logger="agent"):
            await agent.invoke("hello", "test-ctx-m2")

        assert any("M2.achieved" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_agent_milestone_m3_logged(add_agent_to_path, caplog):
    """Unit test: M3 milestone is logged when response is delivered."""
    import logging
    from agent import SampleAgent

    with patch("agent.ChatLiteLLM") as mock_llm_cls, \
         patch("agent.create_checkpointer") as mock_checkpointer, \
         patch("agent.create_agent") as mock_create_agent, \
         patch("agent.SummarizationMiddleware"):

        mock_llm_cls.return_value = MagicMock()
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [MagicMock(content="Hello World")]
        }
        mock_create_agent.return_value = mock_graph
        mock_checkpointer.return_value = MagicMock()

        agent = SampleAgent()
        with caplog.at_level(logging.INFO, logger="agent"):
            chunks = []
            async for chunk in agent.stream("hello", "test-ctx-m3"):
                chunks.append(chunk)

        assert any("M3.achieved" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Integration Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integration_end_to_end(add_agent_to_path):
    """Integration test: end-to-end agent flow with mocked LLM."""
    from agent import SampleAgent

    with patch("agent.ChatLiteLLM") as mock_llm_cls, \
         patch("agent.create_checkpointer") as mock_checkpointer, \
         patch("agent.create_agent") as mock_create_agent, \
         patch("agent.SummarizationMiddleware"):

        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm

        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [MagicMock(content="Hello World")]
        }
        mock_create_agent.return_value = mock_graph
        mock_checkpointer.return_value = MagicMock()

        agent = SampleAgent()

        # Test multiple queries all return Hello World
        for query in ["Hi!", "What time is it?", "Tell me a joke"]:
            result = await agent.invoke(query, f"ctx-{query}")
            assert result.status == "completed"
            assert result.message == "Hello World"
