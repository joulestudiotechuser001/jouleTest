# Specification: hello-world-agent

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent.md](../guidelines-agent.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [x] Read the project input (`product-requirements-document.md`, `intent.md`, or the user prompt that triggered this specification)
- [x] Bootstrap agent code in `assets/hello-world-agent/` using skill `sap-agent-bootstrap` (invoke from inside `assets/hello-world-agent/`, use copy commands — do NOT create files manually)
- [x] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

> No runtime skills are required — the agent has no complex multi-step workflows or domain-specific reference material; its entire logic is a single deterministic "Hello World" response.

## REQ-01: Hello World Response

- [x] Set the agent system prompt (via `@prompt_section`) to instruct the agent to always respond with "Hello World" regardless of any input
- [x] Implement response handling in a plain async helper `_run_agent(query: str) -> str` that returns the string `"Hello World"`
- [x] Wire `_run_agent()` into the `stream()` method: call `_run_agent()` to get the response, then `yield` it — never wrap a `yield` inside `with tracer.start_as_current_span(...)`

## REQ-02: No External Dependencies

- [x] Confirm `requirements.txt` has no external API clients (`requests`, `httpx`, OData clients, etc.)
- [x] Confirm `asset.yaml` has no `requires` entries (no MCP servers needed)
- [x] Confirm the agent runs fully offline (no network calls to SAP APIs or external services)

## REQ-03: Business Step Instrumentation (M1, M2, M3)

- [x] Instrument **M1 – Agent Invoked** inside `_run_agent()`:
  - Log `M1.achieved: agent received incoming request` when a valid message is received
  - Log `M1.missed: agent did not receive or parse the incoming request` if the input is empty or invalid
- [x] Instrument **M2 – Response Generated** inside `_run_agent()`:
  - Log `M2.achieved: Hello World response generated successfully` after constructing the response
  - Log `M2.missed: response generation step did not complete` if an exception is raised before the response is built
- [x] Instrument **M3 – Response Delivered** in `stream()` after yielding the response:
  - Log `M3.achieved: Hello World response delivered to caller` after the response is yielded
  - Log `M3.missed: response delivery did not complete` in the exception handler
- [x] Add OpenTelemetry custom spans for each milestone using `@tracer.start_as_current_span("m1-agent-invoked")` on `_run_agent()` (decorator form) — do NOT use context manager form inside any generator
- [x] Verify `auto_instrument()` is called at the top of `main.py` before any AI framework imports

## Cleanup

- [x] Delete the template runtime skill: `rm -rf assets/hello-world-agent/app/skills/template-skill/`
- [x] Verify `assets/hello-world-agent/app/agent.py` has exactly 5 decorated functions — confirmed `5`

## Testing

- [x] `conftest.py` only sets `IBD_TESTING=true` — no MCP mock needed (no MCP servers used)
- [x] Write unit tests in `assets/hello-world-agent/tests/`:
  - `test_response.py` — 5 tests: Hello World for any input (empty, normal, special chars, long, multiline)
  - `test_milestones.py` — 5 tests: M1, M2, M3 log statements verified, stream delivers Hello World
- [x] Write one integration test `test_integration.py` — 3 tests: invoke returns Hello World, empty message, stream chunk order
- [x] Run `pytest` from `assets/hello-world-agent/` — **37 passed, 0 failed, 72% coverage**
- [x] Verify `assets/hello-world-agent/app/agent.py` has exactly 5 decorated functions — confirmed `5`
- [x] Run final `pytest` (no args) — `test_report.json` generated
- [x] Verify `test_report.json` exists in `assets/hello-world-agent/` — confirmed
