---
repo_name: microsoft/agent-lightning
url: "https://github.com/microsoft/agent-lightning"
stars: 16992
forks: 1488
contributors_count: 31
last_commit_date: "2026-02-11T14:20:42+00:00"
primary_use_case: Workflow Automation
user_tier: Mainstream
total_score: 7
architecture_labels: [LangChain, AutoGen, CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T10:55:00.805681+00:00"
model: auto
duration_s: 89.7
clone_size_kb: 35020
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`microsoft/agent-lightning` is a training/runtime framework for improving LLM agents using reinforcement-style rollouts and trace-based credit assignment, not a single end-user chatbot. In practice, users run a `Trainer` with a `LitAgent` implementation and datasets/resources, and the system executes rollouts, records spans, adapts traces into training data, and runs algorithms (e.g., baseline or APO) to optimize behavior (`agentlightning/trainer/trainer.py:36-59`, `agentlightning/algorithm/apo/apo.py:81-99`). The repo includes concrete agent examples (SQL agent, RAG agent, AutoGen/CrewAI/OpenAI Agents SDK integrations) showing how existing agent stacks can be plugged in and tuned. The output a user gets is improved prompts/policies/resources plus telemetry-backed trajectories/rewards stored in `LightningStore` for iterative training.

## 2. Agent Framework & Architecture

The core framework is **custom Agent Lightning infrastructure**, not LangGraph/AutoGen/CrewAI as the primary runtime. Core classes (`LitAgent`, `LitAgentRunner`, `Trainer`, `Algorithm`) are all in-repo abstractions (`agentlightning/litagent/litagent.py:45-53`, `agentlightning/runner/agent.py:60-67`, `agentlightning/trainer/trainer.py:36-53`, `agentlightning/algorithm/base.py:25-33`).

That said, Agent Lightning is explicitly designed to train/trace agents from external ecosystems. The codebase and examples import and run **LangGraph/LangChain** (`examples/spider/sql_agent.py:22-29`), **AutoGen** (`examples/calc_x/calc_agent.py:11-15`), **CrewAI** (`examples/tinker/q20_agent.py:17-21`), and **OpenAI Agents SDK** (`examples/rag/rag_agent.py:9-13`). The adapter layer normalizes heterogeneous traces and extracts agent identities across systems (OpenAI Agent SDK, AgentOps decorators, AutoGen teams, LangGraph chains, Weave) (`agentlightning/adapter/triplet.py:317-366`).

Architecturally, “intelligence” is split across: (1) user-defined agent prompts/logic in example agents, (2) rollout execution/tracing in runners, and (3) algorithmic optimization over stored traces. The trainer wires algorithm and runner bundles into an execution strategy (often client-server), runners dequeue rollouts and call agent rollout methods inside trace contexts, and adapters convert spans into triplets/messages for learning (`agentlightning/trainer/trainer.py:430-439`, `agentlightning/runner/agent.py:663-681`, `agentlightning/adapter/triplet.py:831-854`).

## 3. Orchestration Pattern

Closest match: **event-driven (store-queued workflow orchestration)**, with optional graph-style orchestration inside individual example agents.

At framework level, control flow is queue/event based: algorithms enqueue rollouts and update resources; runners poll/dequeue work and execute agents; shared stop events coordinate shutdown (`agentlightning/runner/agent.py:763-782`, `agentlightning/execution/client_server.py:46-57`).

```394:401:agentlightning/trainer/trainer.py
def fit(...):
    ...
    algorithm_bundle = functools.partial(self._algorithm_bundle, ...)
    runner_bundle = functools.partial(self._runner_bundle, agent=agent)
    self.strategy.execute(algorithm_bundle, runner_bundle, self.store)
```

```763:768:agentlightning/runner/agent.py
while not (event is not None and event.is_set()):
    logger.debug(f"{self._log_prefix()} Try to poll for next rollout.")
    next_rollout = await store.dequeue_rollout(worker_id=self.get_worker_id())
    ...
```

Inside tasks, users can define other patterns (e.g., LangGraph state machine with conditional loop in SQL example) (`examples/spider/sql_agent.py:366-382`), but that is pluggable agent logic rather than the core orchestrator.

## 4. Tools & External Integrations

- **LLM APIs (OpenAI-compatible, Azure OpenAI, vLLM)**
  - Direct OpenAI/Azure calls in examples (`examples/azure/capital_agent.py:87-101`, `examples/apo/room_selector.py:168-177`).
  - LangChain/OpenAI model init (`examples/spider/sql_agent.py:207-226`).
- **LiteLLM proxy + OpenTelemetry tracing pipeline**
  - In-repo LLM proxy server with middleware/callbacks, sequence-id injection, OTEL export to store (`agentlightning/llm_proxy.py:1007-1016`, `agentlightning/llm_proxy.py:536-572`, `agentlightning/llm_proxy.py:1179-1204`).
- **MCP integrations**
  - AutoGen MCP workbench tool server (`examples/calc_x/calc_agent.py:14-15`, `examples/calc_x/calc_agent.py:75-83`).
  - OpenAI Agents SDK MCP SSE retriever (`examples/rag/rag_agent.py:11`, `examples/rag/rag_agent.py:50-66`).
- **Databases / SQL tools**
  - LangChain SQLDatabase and SQL query tool invocation (`examples/spider/sql_agent.py:23-24`, `examples/spider/sql_agent.py:294-301`).
- **Tracing/observability backends**
  - AgentOps, LiteLLM, optional LangChain instrumentation toggles (`agentlightning/instrumentation/__init__.py:43-71`).
- **Workflow frameworks plugged into Lightning**
  - LangGraph (`examples/spider/sql_agent.py:27-29`), AutoGen (`examples/calc_x/calc_agent.py:11-14`), CrewAI (`examples/tinker/q20_agent.py:17-21`), OpenAI Agents SDK (`examples/rag/rag_agent.py:9-13`).

## 5. Notable Code Walkthrough

- `agentlightning/trainer/trainer.py:36-59, 430-439, 487-555`  
  Defines the core Trainer orchestration: binds algorithm/adapter/store/runner, then executes algorithm and runner bundles via strategy; this is the runtime backbone.

- `agentlightning/runner/agent.py:621-701, 737-782`  
  Implements rollout execution lifecycle (resource fetch, trace context, sync/async agent call, post-processing/reward handling) and continuous dequeue loop.

- `agentlightning/adapter/triplet.py:317-366, 398-477, 831-854`  
  Critical normalization logic: detects agent names across frameworks, finds/matches LLM call spans and rewards, and converts traces into trajectory triplets.

- `agentlightning/llm_proxy.py:536-572, 1007-1062, 1250-1282`  
  Shows production-grade proxy integration: rollout-aware request rewriting, callback/middleware wiring, and server lifecycle for trace-rich model serving.

- `examples/tinker/q20_agent.py:229-320`  
  Representative true multi-agent example: CrewAI flow coordinates player + answerer + optional search tool in iterative turns with routing and termination logic.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** is accurate. Agent Lightning automates the end-to-end workflow of (a) scheduling agent rollouts, (b) collecting/tracing interactions, (c) converting traces to training signals, and (d) iteratively updating prompts/resources via algorithms (`agentlightning/trainer/trainer.py:37-53`, `agentlightning/algorithm/apo/apo.py:430-510`). It is less about one fixed “assistant” and more about automating optimization loops for many agent workflows (SQL QA, RAG, tool-using agents, game-like multi-agent flows).  

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Framework-agnostic training scaffold that can wrap diverse agent stacks (LangGraph, AutoGen, CrewAI, OpenAI Agents SDK).
  - Strong telemetry-first design: trace capture, hierarchy repair, reward matching, and adapters for learning data.
  - Decoupled architecture (algorithm/runner/store/strategy) supports distributed execution and reproducible rollout pipelines.
  - Practical tool/use-case examples with real integrations (MCP, SQL DBs, tool calls, proxy serving).
  - Includes true multi-agent coordination examples (e.g., CrewAI player/answerer flow).

- **Limitations:**
  - Core library does not provide a single canonical built-in multi-agent planner/router; coordination is mostly user-defined in examples.
  - Significant operational complexity (proxy modes, callback state, tracing dependencies) may raise setup/debug burden.
  - Quality depends on external framework traces being complete; hierarchy repair heuristics imply imperfect upstream trace structures.
  - Some docs/comments indicate fragile areas (streaming/tracer conflicts, event-loop issues in LiteLLM integration).

- **Research relevance:**
  - Evidence for **training-time orchestration** of agent systems via trace-to-trajectory conversion and reward attribution.
  - Useful reference for studying **cross-framework observability** and interoperability in agent engineering.
  - Demonstrates event-driven rollout execution at scale with algorithm/worker decoupling.
  - Provides empirical substrate for comparing single-agent vs multi-agent behaviors under a common optimization pipeline.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
