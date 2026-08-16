"""Integration test — end-to-end agent flow with LLM mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def agent(add_agent_to_path):
    with patch("agent.create_checkpointer", return_value=MagicMock()), \
         patch("agent.SummarizationMiddleware", return_value=MagicMock()):
        from agent import SampleAgent
        return SampleAgent()


@pytest.mark.asyncio
async def test_invoke_returns_hello_world(agent):
    """End-to-end: invoke() must return 'Hello World' with LLM mocked."""
    response = await agent.invoke("Tell me something", "ctx-integration")
    assert response.status == "completed"
    assert response.message == "Hello World"


@pytest.mark.asyncio
async def test_invoke_with_empty_message(agent):
    """End-to-end: invoke() with empty message still returns Hello World."""
    response = await agent.invoke("", "ctx-integration-2")
    assert response.status == "completed"
    assert response.message == "Hello World"


@pytest.mark.asyncio
async def test_stream_yields_processing_then_hello_world(agent):
    """Stream yields a processing chunk followed by Hello World completion."""
    chunks = []
    async for chunk in agent.stream("hello?", "ctx-stream"):
        chunks.append(chunk)

    assert len(chunks) >= 2
    assert chunks[0]["is_task_complete"] is False
    assert chunks[0]["content"] == "Processing..."
    final = chunks[-1]
    assert final["is_task_complete"] is True
    assert final["content"] == "Hello World"
