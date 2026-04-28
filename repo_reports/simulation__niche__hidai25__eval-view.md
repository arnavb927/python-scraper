---
repo_name: hidai25/eval-view
url: "https://github.com/hidai25/eval-view"
stars: 91
forks: 21
contributors_count: 15
last_commit_date: "2026-04-22T21:13:25+00:00"
primary_use_case: Simulation
user_tier: Niche
total_score: 3
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T17:08:19.673630+00:00"
model: auto
duration_s: 87.0
clone_size_kb: 150357
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`evalview` is a regression-testing harness for LLM agents, not an agent runtime itself. A user typically runs CLI commands like `evalview snapshot`, `evalview check`, and `evalview simulate` to execute test cases against an external agent endpoint and compare behavior against saved golden traces (`evalview/commands/check_cmd.py:567-888`, `evalview/commands/simulate_cmd.py:141-210`). The system captures tool calls, outputs, timing, and cost, then computes diffs and a release verdict. In practice, it solves “silent behavior drift” problems (model/tool/output changes) in CI or local workflows by turning agent runs into repeatable checks.

## 2. Agent Framework & Architecture

This repo uses a **custom evaluation framework** with adapter integrations for external frameworks/providers, rather than implementing its own LangGraph/CrewAI multi-agent runtime. Evidence: `AgentAdapter` is an abstract interface (`evalview/adapters/base.py:9-41`), and `create_adapter` dynamically instantiates adapters for `langgraph`, `crewai`, `openai-assistants`, `http`, etc. (`evalview/core/adapter_factory.py:12-75`).

Architecture is pipeline-centric: load tests -> build adapter -> execute target agent -> evaluate -> diff against golden -> produce verdict (`evalview/commands/shared.py:633-797`, `evalview/commands/check_cmd.py:1176-1213`). The “intelligence” in EvalView mostly lives in evaluator logic and verdict heuristics (scoring, drift classification, recommendation generation), not in planner/router prompts (`evalview/evaluators/evaluator.py:55-223`, `evalview/commands/check_cmd.py:183-358`).

There is also a simulation subsystem that wraps an adapter with deterministic mocks for tool/HTTP/response behaviors (`evalview/core/simulation.py:160-334`), but this still evaluates an external agent execution path rather than orchestrating multiple internal agents.

## 3. Orchestration Pattern

Closest match: **sequential workflow automation pipeline** (with optional parallel test execution), not hierarchical/swarm/graph multi-agent orchestration.

Control flow is explicit and linear per test in `_execute_check_tests`:

```538:547:evalview/commands/shared.py
if tc.is_multi_turn:
    return await _execute_multi_turn_trace(tc, adapter)
return await adapter.execute(tc.input.query, tc.input.context)
```

Then evaluate and diff:

```694:703:evalview/commands/shared.py
result = await evaluator.evaluate(tc, trace)
golden_variants = store.load_all_golden_variants(tc.name)
diff = await diff_engine.compare_multi_reference_async(
    golden_variants, trace, result.score
)
```

At command level, `check` composes these outputs into release gating signals/verdict:

```1183:1190:evalview/commands/check_cmd.py
verdict_output = _compute_verdict_payload(
    diffs=diffs,
    results=results,
    drift_tracker=drift_tracker,
    execution_failures=execution_failures,
)
```

## 4. Tools & External Integrations

- **External agent endpoints (HTTP/REST):** generic POST execution with trace extraction in `HTTPAdapter` (`evalview/adapters/http_adapter.py:80-203`).
- **LangGraph integration:** supports invoke + cloud thread/run streaming patterns (`evalview/adapters/langgraph_adapter.py:25-100`, `101-388`).
- **CrewAI integration:** parses Crew task/agent execution payloads (`evalview/adapters/crewai_adapter.py:26-187`).
- **OpenAI Assistants API:** thread/run polling + run-step tool extraction (`evalview/adapters/openai_assistants_adapter.py:51-199`, `210-311`).
- **LLM judge providers:** OpenAI/Anthropic/Gemini/Grok/DeepSeek/HuggingFace/Ollama via `LLMClient` for evaluation scoring (`evalview/core/llm_provider.py:73-418`).
- **MCP server exposure:** exposes EvalView CLI actions as MCP tools (`evalview/mcp_server.py:20-412`, `415-483`).
- **Cloud sync/push:** optional cloud upload/pull of goldens/results in command helpers (`evalview/commands/shared.py:820-870`, `evalview/commands/check_cmd.py:1292-1355`).
- **Simulation mocks:** mock tool calls/HTTP/LLM responses for hermetic test runs (`evalview/core/simulation.py:11-21`, `190-334`).

## 5. Notable Code Walkthrough

- `evalview/commands/check_cmd.py:567-1384` - Main regression gate command; handles test filtering, statistical mode, healing, drift/verdict computation, reporting, and CI exit code logic.
- `evalview/commands/shared.py:633-797` - Core execution pipeline (`execute -> evaluate -> diff`) reused by commands; this is the operational heart of EvalView.
- `evalview/evaluators/evaluator.py:55-223` - Orchestrates scoring dimensions (tools/sequence/output/cost/latency/safety/PII) and pass/fail logic; this defines what “regression” means.
- `evalview/core/simulation.py:160-334` - Deterministic simulation harness using mock interceptors and variant fan-out; key to its simulation capability.
- `evalview/adapters/langgraph_adapter.py:86-100` and `evalview/adapters/openai_assistants_adapter.py:51-199` - Representative framework adapters that normalize heterogeneous agent traces into EvalView’s common `ExecutionTrace` schema.

## 6. Use-Case Mapping

The assigned label **Simulation** is partially valid because the repo includes a real simulation harness (`evalview/core/simulation.py`, CLI in `evalview/commands/simulate_cmd.py`). However, after reading the core flow, the dominant use case is **Workflow Automation**: automated regression gating pipelines for agent behavior in local dev/CI (`evalview/commands/check_cmd.py`, `evalview/commands/shared.py`). So Simulation is a feature, but not the primary product behavior.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong adapter abstraction lets one evaluator pipeline work across many agent backends (`evalview/adapters/base.py`, `evalview/core/adapter_factory.py`).
  - Clear, production-oriented regression workflow (snapshot/check/diff/verdict) with CI-friendly exit semantics (`evalview/commands/check_cmd.py`).
  - Rich evaluation stack combines deterministic checks and optional LLM-as-judge (`evalview/evaluators/evaluator.py`).
  - Practical simulation mode with deterministic mocks and branch/variant reporting (`evalview/core/simulation.py`).
  - Good observability and rationale capture hooks in adapters (`evalview/adapters/langgraph_adapter.py`, `evalview/adapters/openai_assistants_adapter.py`).

- **Limitations:**
  - No native multi-agent coordination runtime; it evaluates external agents rather than implementing MAS behaviors internally.
  - Some adapter parsing relies on heuristics over heterogeneous payloads, which may miss edge-case traces (`langgraph_adapter` message/event parsing).
  - Verdict logic is extensive but mostly rule-based; limited explicit formal uncertainty modeling beyond drift tiers.
  - Heavy command modules (`check_cmd.py`) centralize many concerns, increasing maintenance complexity.
  - Dependence on external endpoint conventions means trace fidelity varies by adapter and agent implementation quality.

- **Research relevance:**
  - Useful evidence for **agent evaluation infrastructure** design (trace normalization + golden diffing + CI gating).
  - Demonstrates practical methods for **behavior drift detection** in tool-using LLM systems.
  - Provides a concrete artifact for studying **deterministic vs LLM-judge hybrid scoring** tradeoffs.
  - Relevant to work on **reproducible simulation harnesses** for agent reliability testing.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
