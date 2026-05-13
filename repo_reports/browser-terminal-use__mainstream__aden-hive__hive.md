---
repo_name: aden-hive/hive
url: "https://github.com/aden-hive/hive"
stars: 10124
forks: 5619
contributors_count: 226
last_commit_date: "2026-04-23T04:38:21+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:03:17.394577+00:00"
model: auto
duration_s: 139.9
clone_size_kb: 24728
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`aden-hive/hive` is a production-oriented multi-agent runtime where users run a long-lived “queen” agent session (via the `hive` CLI/server) that can either do work directly or spin up parallel worker agents as a colony. In practice, a user starts a session, chats with the queen, and the system can fan out tasks, manage escalations, and stream worker reports back into the queen conversation. The core output is not just a single LLM answer, but an orchestrated workflow: task planning, tool execution, worker lifecycle control, and persistent session/colony state. The repo includes both the orchestration engine (`core/framework`) and MCP tool servers (`tools/`) for filesystem, browser, terminal, and many external integrations. This is primarily an automation runtime for persistent, multi-step agent operations rather than a simple chatbot.

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework**, not LangGraph/CrewAI/AutoGen. Evidence: the core abstractions are homegrown (`Orchestrator`, `NodeWorker`, `ColonyRuntime`, `AgentLoop`) under `core/framework/*`, with custom LLM/provider interfaces (`core/framework/llm/provider.py`) and LiteLLM backend integration (`core/framework/llm/litellm.py`). I did not find runtime imports of LangGraph/CrewAI-style orchestration frameworks in the main execution path.

Architecture is hybrid and has two key layers:

1. **Node-graph execution layer** (`core/framework/orchestrator/orchestrator.py`, `node_worker.py`): graphs are compiled into per-node workers, each evaluating outgoing edges and activating downstream workers via an event bus. This includes fan-out/fan-in semantics and retry/visit controls.

2. **Queen/colony supervisory layer** (`core/framework/server/queen_orchestrator.py`, `core/framework/host/colony_runtime.py`): a long-lived queen `AgentLoop` acts as user-facing manager; it can spawn parallel worker clones, monitor them, receive escalations/reports, and switch operational phases (independent/incubating/working/reviewing). The “intelligence” is split across: phase-specific prompt blocks (`core/framework/agents/queen/nodes/__init__.py`), dynamic tool gating, and runtime lifecycle tools (`core/framework/tools/queen_lifecycle_tools.py`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker**, with event-driven internals.

- The queen is the manager/supervisor (user-facing, phase-driven), while spawned workers execute delegated tasks and report back (`core/framework/server/queen_orchestrator.py`, `core/framework/host/colony_runtime.py`).
- Inside graph execution, control is event-driven worker activation (node-workers triggering downstream workers), so there is also a graph/event flavor (`core/framework/orchestrator/node_worker.py`, `orchestrator.py`).

Example control-flow evidence:

```1087:1098:core/framework/tools/queen_lifecycle_tools.py
async def run_parallel_workers(
    *,
    tasks: list[dict],
    timeout: float | None = None,
    hard_timeout: float | None = None,
) -> str:
    """Spawn N parallel workers and return immediately.
    ...
    Workers run in the background; each one emits a ``SUBAGENT_REPORT``
```

```1318:1326:core/framework/orchestrator/orchestrator.py
# Create one WorkerAgent per node
workers: dict[str, NodeWorker] = {}
for node_spec in graph.nodes:
    workers[node_spec.id] = NodeWorker(node_spec=node_spec, graph_context=gc)

# Identify entry workers (graph entry node, not based on edge count)
entry_worker_ids = [graph.entry_node]
```

## 4. Tools & External Integrations

- **MCP server ecosystem (primary integration plane)**: tools are loaded via `ToolRegistry` and MCP registry mechanisms (`core/framework/loader/tool_registry.py`, `core/framework/loader/mcp_registry.py`).
- **Browser automation (Playwright-backed GCU MCP server)**: wired in queen MCP config and tool server (`core/framework/agents/queen/mcp_servers.json`, `tools/src/gcu/server.py`).
- **Filesystem tools** (`read_file`, `write_file`, `edit_file`, `search_files`): loaded through `files-tools` MCP server (`core/framework/agents/queen/mcp_servers.json` and default MCP seed in `core/framework/loader/mcp_registry.py`).
- **Terminal tools** (`terminal_exec`, `terminal_rg`, `terminal_find`, PTY/jobs): server exists and is seeded in default local MCP servers (`core/framework/loader/mcp_registry.py:41-62`; server in `tools/src/terminal_tools/server.py`). Also explicitly considered in worker inherited tool policy (`core/framework/server/routes_execution.py:39-55`).
- **Large integration toolbox (email/CRM/search/etc.)** via `hive_tools` / `aden_tools` MCP and credential gating (`core/framework/agents/queen/mcp_servers.json`, `core/framework/loader/tool_registry.py:754-984`).
- **LLM providers** via LiteLLM abstraction (`core/framework/llm/provider.py`, `core/framework/llm/litellm.py`) and model/provider routing logic in config/session code.
- **Event bus / SSE streaming** for inter-agent coordination and UI streaming (`core/framework/host/event_bus.py` referenced throughout server/orchestrator paths).
- **Persistent storage and session state** for conversations, checkpoints, progress DB, worker logs (`core/framework/orchestrator/orchestrator.py`, `core/framework/host/colony_runtime.py`, `core/framework/server/session_manager.py`).

## 5. Notable Code Walkthrough

- `core/framework/server/queen_orchestrator.py:342-1159`  
  Builds the queen runtime: loads MCP tools, partitions phase toolsets, composes dynamic prompts, subscribes to worker reports/escalations, and runs the queen’s long-lived `AgentLoop`.

- `core/framework/tools/queen_lifecycle_tools.py:1087-1330`  
  Implements queen-facing lifecycle primitives like `run_parallel_workers`, including caps, credential preflight, and timeout behavior before/while spawning worker batches.

- `core/framework/host/colony_runtime.py:155-1213`  
  Core multi-worker runtime: spawns worker clones, manages triggers/webhooks/timers, collects reports, applies tool allowlists, and supports overseer mode.

- `core/framework/orchestrator/orchestrator.py:1255-1804`  
  Executes node graphs with workerized/event-driven scheduling, completion/failure subscriptions, activation routing, and result assembly (including fan-out handling).

- `core/framework/orchestrator/node_worker.py:112-515`  
  Defines autonomous node workers that receive activations, execute with retries, evaluate edges, and emit downstream activations/events.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate. The repo absolutely supports browser and terminal operations (GCU and terminal MCP servers are integrated), but those are tool capabilities inside a broader orchestration platform. The dominant behavior in core code is **workflow automation**: manager-worker delegation, persistent sessions, trigger-driven execution, colony lifecycle control, escalations, and reporting.

So a better final category is **Workflow Automation** (with Browser/Terminal as important sub-capabilities rather than the primary identity).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong real runtime architecture for multi-agent coordination (queen manager + parallel workers + event bus).
  - Rich operational tooling: lifecycle controls, escalation routing, worker monitoring, timeout/watchdog behavior.
  - Practical production concerns handled in code: checkpointing, session restore, tool allowlists, credential-aware MCP admission.
  - Dynamic prompt/tool phase model gives explicit governance over what the manager can do at each stage.
  - Broad integration surface through MCP servers and LiteLLM provider abstraction.

- **Limitations:**
  - Complexity is high; control logic is spread across many modules with long files (harder to reason about correctness end-to-end).
  - Heavy dependence on runtime state, event ordering, and side-effectful tools increases debugging burden.
  - Tool/server bootstrapping and compatibility paths (legacy/runtime variants) add operational edge cases.
  - Some architecture mixes paradigms (graph workers + colony workers + queen loop), which can be conceptually dense for contributors.
  - Browser/terminal capabilities are present but can be inconsistently surfaced depending on phase/tool gating and session mode.

- **Research relevance:**
  - Good evidence of **hierarchical LLM MAS** in production-like settings (supervisor + delegated workers).
  - Demonstrates **event-driven coordination** patterns (activation routing, escalation and report channels).
  - Useful for studying **tool governance** in MAS (phase-based tool partitions, allowlists, credential-gated admission).
  - Shows practical mechanisms for **long-horizon agent persistence** (session memory, restore, triggers, background workers).

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
