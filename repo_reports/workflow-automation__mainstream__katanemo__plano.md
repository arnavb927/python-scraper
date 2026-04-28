---
repo_name: katanemo/plano
url: "https://github.com/katanemo/plano"
stars: 6369
forks: 404
contributors_count: 32
last_commit_date: "2026-04-22T18:19:10+00:00"
primary_use_case: Workflow Automation
user_tier: Mainstream
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T13:12:24.440454+00:00"
model: auto
duration_s: 105.2
clone_size_kb: 63570
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`katanemo/plano` is an AI proxy/data-plane that sits between client apps and both LLM providers and external agents, then handles routing, orchestration, filters, and observability for them. In practice, users run the `brightstaff` server (plus Envoy/WASM in full deployment) and send OpenAI-compatible requests to endpoints like `/v1/chat/completions` or `/agents/v1/chat/completions`; Plano then decides which model/agent path to execute and streams results back. The code shows two major operating modes: model routing (single LLM request path) and agent orchestration (multi-agent path). It solves production orchestration concerns (intent-based selection, chain execution, retries, session pinning, tracing/signals) so app teams can keep agent logic in separate services.

## 2. Agent Framework & Architecture

The core orchestration in this repo is **custom**, not LangGraph/CrewAI/LangChain in the runtime data plane. The multi-agent control plane is implemented in Rust under `brightstaff`, especially `handlers/agents` and `router/orchestrator`. For example, agent selection calls a custom `OrchestratorService` and a custom prompt/model wrapper (`OrchestratorModelV1`) rather than any external orchestration library (`crates/brightstaff/src/handlers/agents/selector.rs:106-167`, `crates/brightstaff/src/router/orchestrator.rs:251-328`, `crates/brightstaff/src/router/orchestrator_model_v1.rs:185-313`).

Architecture-wise, there is a clear outer-loop/inner-loop split:  
- **Outer loop (Plano):** classify intent, select agent route(s), execute selected agents in order, run filter chains, and handle metrics/tracing (`crates/brightstaff/src/handlers/agents/orchestrator.rs:207-431`, `crates/brightstaff/src/handlers/agents/pipeline.rs:519-596`).  
- **Inner loop (user agents):** arbitrary HTTP agent services (can use CrewAI/LangChain/custom code). The repo includes demos showing CrewAI and LangChain agents (`demos/agent_orchestration/multi_agent_crewai_langchain/crewai/flight_agent.py:15-17`, `.../langchain/weather_agent.py:14-16`), but these are examples, not the core orchestrator implementation.

The “intelligence” for agent selection lives in prompt-based route classification by the `plano-orchestrator` model: it builds a routing prompt with `<routes>` + `<conversation>`, sends it to an LLM, parses JSON `{"route":[...]}`, and maps route names to agent IDs/models (`crates/brightstaff/src/router/orchestrator_model_v1.rs:117-139`, `:289-387`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with sequential execution**.

- Manager: `AgentSelector` + `OrchestratorService` decide which worker agents should run for a request (`crates/brightstaff/src/handlers/agents/selector.rs:124-167`).  
- Workers: selected agent services are invoked one-by-one; intermediate agent output is inserted back into message history before invoking the next (`crates/brightstaff/src/handlers/agents/orchestrator.rs:264-399`).

Control-flow excerpts:

```243:251:crates/brightstaff/src/handlers/agents/selector.rs
match self
    .orchestrator_service
    .determine_orchestration(messages, Some(usage_preferences), request_id)
    .await
{
```

```279:287:crates/brightstaff/src/handlers/agents/orchestrator.rs
for (agent_index, selected_agent) in selected_agents.iter().enumerate() {
    let agent_name = selected_agent.id.clone();
    let is_last_agent = agent_index == agent_count - 1;
```

This is not peer-to-peer swarm behavior; control is centralized and ordered by the orchestrator.

## 4. Tools & External Integrations

- **LLM providers (OpenAI-compatible + many vendors):** configured and routed through provider abstractions in `common`/`hermesllm`; model/provider mapping comes from config (`crates/common/src/configuration.rs:362-403`, `crates/brightstaff/src/handlers/llm/mod.rs:646-718`).
- **Agent HTTP endpoints:** selected agents are invoked via HTTP `/v1/chat/completions` through pipeline code (`crates/brightstaff/src/handlers/agents/pipeline.rs:570-596`).
- **MCP tool/filter integrations:** pipeline supports MCP JSON-RPC init and `tools/call` for filters (`crates/brightstaff/src/handlers/agents/pipeline.rs:185-232`, `:347-444`, `:553-559`).
- **Input/output filter chains over raw bytes:** model listener and streaming path can run chains of filter agents (`crates/brightstaff/src/handlers/llm/mod.rs:188-252`, `crates/brightstaff/src/streaming.rs:492-592`).
- **State storage for conversation continuity:** memory or Postgres backends for Responses API state (`crates/brightstaff/src/main.rs:353-391`, `crates/brightstaff/src/handlers/llm/mod.rs:549-639`).
- **Session cache (affinity/pinning):** route/model pinned by session ID via memory/redis-backed cache abstraction (`crates/brightstaff/src/router/orchestrator.rs:115-165`, `crates/brightstaff/src/handlers/llm/mod.rs:96-119`).
- **Metrics/tracing:** OpenTelemetry propagation/spans plus custom signal analysis and Prometheus metrics (`crates/brightstaff/src/streaming.rs:266-385`).

## 5. Notable Code Walkthrough

- `crates/brightstaff/src/handlers/agents/orchestrator.rs:48-431`  
  Main runtime for `/agents/...` requests. It parses agent requests, asks the orchestrator which agents to run, executes selected agents in sequence, and streams final output.

- `crates/brightstaff/src/handlers/agents/selector.rs:106-167`  
  Converts listener agent descriptions into orchestration preferences, calls orchestrator inference, and maps returned routes back to configured agent chains (with default fallback).

- `crates/brightstaff/src/router/orchestrator_model_v1.rs:117-139,185-387`  
  Defines the orchestration prompt template and request/response logic for route classification. Includes token-budget trimming and route-to-model mapping.

- `crates/brightstaff/src/handlers/agents/pipeline.rs:519-596`  
  Executes raw filter chains (HTTP or MCP) and performs actual agent invocation. This is where external tool/filter services are wired into request flow.

- `crates/brightstaff/src/main.rs:104-350,474-510`  
  Bootstraps app state (providers, listeners, filters, orchestrator config) and routes incoming requests to model path vs agent path (`/agents`).

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. Plano automates multi-step AI workflows by: (1) classifying intent, (2) selecting one or more specialized agents/models, (3) chaining them with intermediate context passing, and (4) applying standardized filters/telemetry/session behavior around the flow (`crates/brightstaff/src/handlers/agents/selector.rs:124-167`, `crates/brightstaff/src/handlers/agents/orchestrator.rs:264-399`, `crates/brightstaff/src/handlers/agents/pipeline.rs:519-565`). This is workflow orchestration infrastructure rather than a single task-specific assistant.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear outer-loop orchestration abstraction decoupled from inner-loop agent implementations (`docs/source/concepts/agents.rst:24-68` reflected in runtime code).
  - Production-oriented routing internals: session pinning, configurable model selection, and route caching (`crates/brightstaff/src/router/orchestrator.rs:129-247`).
  - Practical multi-agent chain execution with explicit intermediate message handoff (`crates/brightstaff/src/handlers/agents/orchestrator.rs:374-399`).
  - Strong observability hooks (trace propagation, signal analysis, per-request metrics) across orchestration path (`crates/brightstaff/src/streaming.rs:266-385`).
  - Extensible filter mechanism supporting both plain HTTP and MCP-based tool calls (`crates/brightstaff/src/handlers/agents/pipeline.rs:553-559`).

- **Limitations:**
  - Multi-agent chain semantics are mostly linear; no explicit DAG/parallel branch execution in the core orchestrator path (`crates/brightstaff/src/handlers/agents/orchestrator.rs:279-399`).
  - Route decision robustness depends on a single LLM JSON response format (`{"route":[...]}`), with only light sanitation (`crates/brightstaff/src/router/orchestrator_model_v1.rs:323-338`, `:436-438`).
  - Limited support for concurrent multi-tool calls in prompt gateway path (explicit warning: multiple tool calls not supported) (`crates/prompt_gateway/src/stream_context.rs:310-316`).
  - Heavy behavior encoded in config + prompt text can make formal verification of routing decisions difficult (`crates/brightstaff/src/router/orchestrator_model_v1.rs:117-139`).

- **Research relevance:**
  - Real-world example of **LLM-as-router** for selecting among multiple specialized agents.
  - Evidence of a centralized **manager-worker orchestration** architecture in production middleware.
  - Useful case study for combining orchestration with observability/signals and session-memory constraints.
  - Demonstrates framework-agnostic MAS infrastructure where inner agents can be CrewAI/LangChain/custom without changing outer-loop control.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
