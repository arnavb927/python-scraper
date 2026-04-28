---
repo_name: jd-opensource/JoySafeter
url: "https://github.com/jd-opensource/JoySafeter"
stars: 259
forks: 51
contributors_count: 5
last_commit_date: "2026-04-14T11:59:07+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 5
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents]
generated_at: "2026-04-27T14:40:38.958429+00:00"
model: auto
duration_s: 96.1
clone_size_kb: 77722
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

JoySafeter is a full-stack platform for designing and running autonomous agent workflows, where users build node-edge graphs in a visual editor and execute them through a backend runtime. In practice, a user creates/edits an agent graph (manager + worker nodes, tools, prompts), launches a run via chat/websocket APIs, and receives streamed events, tool calls, and final outputs. The backend compiles stored graph definitions into executable LangGraph-compatible runnables and supports pause/resume, persisted run snapshots, and run replay. It also includes a “Copilot” mode that can auto-generate or modify workflow graphs from natural-language requests, then persist those graph edits.

## 2. Agent Framework & Architecture

The repository **actually uses LangChain + LangGraph + DeepAgents** (not CrewAI/AutoGen). Evidence: `langchain`/`langgraph`/`deepagents` are direct dependencies in `backend/pyproject.toml:27-33`, and agent creation uses LangChain’s `create_agent(...)` in `backend/app/core/agent/sample_agent.py:12-15` and `backend/app/core/graph/deep_agents/agent_factory.py:59-66`. Graph execution is treated as compiled state graphs (`CompiledStateGraph`) in `backend/app/services/graph_service.py:11` and built via `build_deep_agents_graph(...)` in `backend/app/services/graph_service.py:887-897`.

Architecturally, runtime execution is centered on a **DeepAgents two-level hierarchy**: one root manager agent plus child worker agents extracted from persisted graph nodes/edges (`backend/app/core/graph/deep_agents/config.py:110-157`). The builder resolves node configs, tools, models, optional memory middleware, and then constructs the root via `create_deep_agent(..., subagents=[...])` (`backend/app/core/graph/deep_agents/builder.py:147-205`). Worker types are polymorphic: standard LLM workers, code-execution workers, or remote A2A workers (`backend/app/core/graph/deep_agents/agent_factory.py:50-175`).

There is a second multi-agent layer in Copilot “deepagents mode”: a manager delegates to sub-agents (`requirements-analyst`, `workflow-architect`, `validator`) to synthesize graph-edit actions (`backend/app/core/copilot_deepagents/manager.py:73-125`, `backend/app/core/copilot_deepagents/runner.py:162-205`). So “intelligence” is split across node system prompts/config in stored graphs plus hardcoded orchestration prompts in `backend/app/core/copilot_deepagents/prompts/*.md`.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)** with graph-backed execution and resumability.  
The core runtime explicitly enforces a root + children structure and composes subagents under a root DeepAgent (`backend/app/core/graph/deep_agents/config.py:116-157`, `backend/app/core/graph/deep_agents/builder.py:190-205`).

Example control-flow excerpt (root building workers, then manager):
```187:205:backend/app/core/graph/deep_agents/builder.py
subagents = []
for cfg in child_configs:
    agent = await _build_worker(...)
    subagents.append(agent)

root_agent = create_deep_agent(
    model=root_model,
    system_prompt=root_prompt,
    tools=root_tools,
    subagents=subagents,
    ...
)
```

Example execution-flow excerpt (compiled graph streamed as events):
```270:274:backend/app/websocket/chat_turn_executor.py
async for event in built_graph.astream_events(
    {"messages": [module.HumanMessage(content=enriched_message)], "context": initial_context},
    config=config,
    version="v2",
):
```

This is not peer-to-peer swarm behavior; workers are selected/orchestrated by a central manager agent definition and graph topology.

## 4. Tools & External Integrations

- **MCP tools/servers**: MCP tools are resolved from per-user registry entries (`server::tool`) in `backend/app/core/agent/node_tools.py:439-451`; registry manages MCP tool metadata and lookup in `backend/app/core/tools/tool_registry.py:150-188`.
- **Web research/search**: Tavily-backed search plus webpage fetch-to-markdown tooling in `backend/app/core/tools/builtin/research_tools.py:50-104`.
- **Filesystem/sandbox execution**: DeepAgents filesystem middleware and sandbox backends are used for agent workspaces and skills (`backend/app/core/agent/sample_agent.py:9-21`, `backend/app/core/graph/deep_agents/builder.py:100-107`).
- **Code execution (local or Docker sandbox)**: Code-agent workers route tasks to local or backend executors (`backend/app/core/graph/deep_agents/agent_factory.py:183-206`), with Docker availability checks in `backend/app/core/graph/deep_agents/builder.py:80-112`.
- **A2A remote agent protocol**: External agent calls via A2A `message/send` and `tasks/get` with retries/polling in `backend/app/core/a2a/client.py:296-479`.
- **LLM providers (multi-vendor)**: Provider abstraction/factory for OpenAI-compatible, Anthropic, Gemini, Ollama, etc. in `backend/app/core/model/factory.py:17-43` and provider modules under `backend/app/core/model/providers/`.
- **Observability/persistence infra**: Event-sourced run snapshots via Redis/DB and websocket broadcasting in `backend/app/services/run_service.py:515-638`.

## 5. Notable Code Walkthrough

- `backend/app/core/graph/deep_agents/builder.py:37-217`  
  Main compilation pipeline: resolve graph node configs, optional Docker sandbox, preload skills, resolve models/tools/memory, then build a root DeepAgent with subagents. This is the backbone converting stored graph definitions into executable agent systems.

- `backend/app/core/graph/deep_agents/agent_factory.py:50-175`  
  Defines how each worker type runs: standard LangChain agent, code agent loop with executable backends, or remote A2A worker. It captures the heterogeneous “agent team” behavior at runtime.

- `backend/app/services/graph_service.py:805-907`  
  Fetches graph/node/edge records, performs permission checks and compile caching, and calls `build_deep_agents_graph` to produce runnable graphs. This connects persistence/UI-authored workflows to execution.

- `backend/app/websocket/chat_turn_executor.py:115-287`  
  Executes turns by invoking `built_graph.astream_events(...)`, transforms runtime events into client SSE/WS events, and handles run lifecycle concerns (interrupt/resume/stop/finalize).

- `backend/app/core/copilot_deepagents/manager.py:128-195`  
  Implements a meta-agent that uses manager + specialist subagents to generate graph-edit actions (`create_node`, `connect_nodes`, etc.), demonstrating a second-order multi-agent “agent that builds agents” workflow.

## 6. Use-Case Mapping

Although the upstream assignment says **Code Generation**, this repository is better categorized as **Workflow Automation**. Its primary runtime artifact is not source code files, but executable **agent workflow graphs** (nodes, edges, tools, prompts) that are compiled and run with stateful orchestration (`backend/app/services/graph_service.py:805-907`, `backend/app/core/graph/deep_agents/builder.py:37-217`).  

It does contain code-oriented capabilities (code-agent executor, skill creation helpers), but those are components inside a larger orchestration platform. The dominant product behavior is: users define/auto-generate workflows, execute them, stream/intervene, and persist runs.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent hierarchy with explicit manager/subagent construction (`backend/app/core/graph/deep_agents/builder.py:147-205`).
  - Supports heterogeneous workers (LLM, code execution, remote A2A) in one orchestration fabric (`backend/app/core/graph/deep_agents/agent_factory.py:80-175`).
  - Strong operational lifecycle: event-sourced runs, snapshots, websocket replay, heartbeats (`backend/app/services/run_service.py:39-638`).
  - Practical tool ecosystem integration (MCP, Tavily, filesystem/sandbox, provider abstraction).
  - Copilot itself is agentic, using specialist subagents to design/validate workflows (`backend/app/core/copilot_deepagents/manager.py:73-125`).

- **Limitations:**
  - Hierarchy is constrained to two levels (manager -> children), limiting deeper recursive team structures (`backend/app/core/copilot_deepagents/prompts/manager.md:87-92`).
  - Tool resolution failures are often downgraded to warnings and empty tool lists, which can silently degrade capability (`backend/app/core/graph/deep_agents/tool_resolver.py:42-44`).
  - Heavy complexity and multiple orchestration paths (standard copilot vs deepagents mode) increase maintenance and reasoning overhead (`backend/app/services/copilot_service.py:104-156`).
  - Some behavior relies on prompt-level policy constraints instead of strongly enforced programmatic constraints (e.g., Copilot phase discipline in manager prompt file).
  - Runtime security boundary depends on executor mode and environment setup (Docker availability fallback logic) (`backend/app/core/graph/deep_agents/builder.py:80-112`).

- **Research relevance:**
  - Concrete example of production-style hierarchical MAS with mixed worker modalities (LLM/code/remote protocol agents).
  - Useful evidence for event-sourced observability and state management in long-running agent workflows.
  - Demonstrates “agentic meta-programming”: an agent team generating/updating another agent workflow graph.
  - Shows integration pattern between visual workflow authoring and runtime MAS compilation/execution.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
