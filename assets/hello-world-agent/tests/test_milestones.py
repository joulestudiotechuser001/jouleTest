"""Unit tests for M1, M2, M3 milestone log statements."""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def agent(add_agent_to_path):
    with patch("agent.create_checkpointer", return_value=MagicMock()), \
         patch("agent.SummarizationMiddleware", return_value=MagicMock()):
        from agent import SampleAgent
        return SampleAgent()


@pytest.mark.asyncio
async def test_m1_achieved_logged(agent, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="agent"):
        await agent._run_agent("test input")
    assert any("M1.achieved" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_m2_achieved_logged(agent, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="agent"):
        await agent._run_agent("test input")
    assert any("M2.achieved" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_m3_achieved_logged(agent, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="agent"):
        chunks = []
        async for chunk in agent.stream("test input", "ctx-1"):
            chunks.append(chunk)
    assert any("M3.achieved" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_stream_delivers_hello_world(agent):
    chunks = []
    async for chunk in agent.stream("any message", "ctx-1"):
        chunks.append(chunk)
    final = next((c for c in chunks if c.get("is_task_complete")), None)
    assert final is not None
    assert final["content"] == "Hello World"


@pytest.mark.asyncio
async def test_m1_m2_both_logged_on_valid_input(agent, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="agent"):
        result = await agent._run_agent("valid input")
    messages = [r.message for r in caplog.records]
    assert any("M1.achieved" in m for m in messages)
    assert any("M2.achieved" in m for m in messages)
    assert result == "Hello World"
