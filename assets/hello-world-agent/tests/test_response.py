"""Unit tests for _run_agent() — verifies Hello World response for any input."""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def agent(add_agent_to_path):
    with patch("agent.create_checkpointer", return_value=MagicMock()), \
         patch("agent.SummarizationMiddleware", return_value=MagicMock()):
        from agent import SampleAgent
        return SampleAgent()


@pytest.mark.asyncio
async def test_run_agent_returns_hello_world(agent):
    result = await agent._run_agent("Hello")
    assert result == "Hello World"


@pytest.mark.asyncio
async def test_run_agent_empty_string(agent):
    result = await agent._run_agent("")
    assert result == "Hello World"


@pytest.mark.asyncio
async def test_run_agent_special_characters(agent):
    result = await agent._run_agent("!@#$%^&*()")
    assert result == "Hello World"


@pytest.mark.asyncio
async def test_run_agent_long_input(agent):
    result = await agent._run_agent("a" * 10000)
    assert result == "Hello World"


@pytest.mark.asyncio
async def test_run_agent_multiline_input(agent):
    result = await agent._run_agent("line1\nline2\nline3")
    assert result == "Hello World"
