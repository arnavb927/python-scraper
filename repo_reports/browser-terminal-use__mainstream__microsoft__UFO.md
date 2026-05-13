---
repo_name: microsoft/UFO
url: "https://github.com/microsoft/UFO"
stars: 8498
forks: 1012
contributors_count: 29
last_commit_date: "2026-04-14T10:54:02+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:09:30.564980+00:00"
model: auto
duration_s: 173.8
clone_size_kb: 117876
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`microsoft/UFO` is an agentic automation system that lets a user run natural-language tasks against desktop apps/devices, then have LLM agents plan and execute actions through tool calls. In the classic UFO path, users run `python -m ufo ...` and the system creates sessions/rounds where a host agent delegates subtasks to app agents (`ufo/ufo.py:51-75`, `ufo/module/sessions/session.py:106-131`). In the newer Galaxy path, users run `python -m galaxy ...` to generate and execute a DAG (“constellation”) of tasks across devices (`galaxy/galaxy.py:191-250`, `galaxy/session/galaxy_session.py:225-277`). The output is executable task progress plus logs/trajectories, screenshots/UI trees, and structured results (`ufo/module/basic.py:315-389`, `galaxy/session/galaxy_session.py:344-360`).

## 2. Agent Framework & Architecture

This repo is primarily a **custom multi-agent framework**, not CrewAI/LangGraph/AutoGen. I do not see those orchestration frameworks used in the runtime control loop; orchestration is implemented via custom state machines, processors, and event bus (`ufo/module/basic.py:156-191`, `ufo/agents/states/*.py`, `galaxy/agents/constellation_agent_states.py:63-140`, `galaxy/constellation/orchestrator/orchestrator.py:143-220`).  

It does use **LangChain components** for retrieval/indexing (FAISS docs/vector search), but that is for RAG utilities, not core orchestration (`ufo/rag/web_search.py:6-9`, `ufo/rag/web_search.py:100-109`, `ufo/llm/llm_call.py:91-99` indirectly through service adapters).  

Architecture has two major agent systems:
- **UFO (desktop-first manager/worker):** `HostAgent` plans/routes and creates `AppAgent`/operator subagents (`ufo/agents/agent/host_agent.py:313-364`). Round execution loops over agent states and can swap active agent/state each step (`ufo/module/basic.py:161-175`).
- **Galaxy (DAG multi-agent orchestration):** `ConstellationAgent` creates/edits a task DAG and `TaskConstellationOrchestrator` executes ready tasks asynchronously with event-driven synchronization (`galaxy/agents/constellation_agent.py:307-416`, `galaxy/constellation/orchestrator/orchestrator.py:394-433`).

## 3. Orchestration Pattern

Closest match: **hybrid hierarchical + event-driven graph orchestration**.

- **Hierarchical (manager-worker) in UFO:** Host agent assigns subagent, then control returns to host after subtask completion (`ufo/agents/states/host_agent_state.py:176-223`, `ufo/agents/states/app_agent_state.py:149-168`).
- **Graph/event-driven in Galaxy:** A DAG is executed by scheduling ready tasks concurrently and reacting to task events (`galaxy/constellation/orchestrator/orchestrator.py:425-491`, `galaxy/agents/constellation_agent_states.py:190-227`).

Example control transfer (Host -> App agent):
```ufo/agents/states/host_agent_state.py:189-213
agent.create_subagent(context)
...
next_agent = self.next_agent(agent)
...
if type(next_agent) == OpenAIOperatorAgent:
    return ContinueOpenAIOperatorState()
else:
    return ContinueAppAgentState()
```

Example DAG scheduling/event loop:
```galaxy/constellation/orchestrator/orchestrator.py:425-433
ready_tasks = constellation.get_ready_tasks()
await self._schedule_ready_tasks(ready_tasks, constellation)
await self._wait_for_task_completion()
...
await self._wait_for_all_tasks()
```

## 4. Tools & External Integrations

- **MCP tool ecosystem (core execution substrate):** tools are discovered/registered from local/http/stdio MCP servers, then invoked via FastMCP client (`ufo/client/computer.py:283-343`, `ufo/client/computer.py:467-510`, `ufo/client/mcp/mcp_server_manager.py:171-252`).
- **Desktop/app action execution:** command dispatcher routes `Command` objects to per-agent “Computer” instances and executes actions with early-exit on failures (`ufo/module/dispatcher.py:93-131`, `ufo/client/computer.py:693-787`).
- **Browser/online retrieval (Bing API):** `BingSearchWeb` calls Bing Search REST and builds LangChain `Document`s (`ufo/rag/web_search.py:28-51`, `ufo/rag/web_search.py:53-77`).
- **Vector store / RAG:** FAISS index creation for retrieved docs (`ufo/rag/web_search.py:100-109`).
- **Multi-provider LLM backend:** a provider-agnostic completion layer selects service by `API_TYPE`/model and supports backup model fallback (`ufo/llm/llm_call.py:80-111`).
- **Event bus for distributed coordination in Galaxy:** orchestration and observers communicate by published task/constellation events (`galaxy/constellation/orchestrator/orchestrator.py:376-391`, `galaxy/session/galaxy_session.py:279-319`).

## 5. Notable Code Walkthrough

- `ufo/module/basic.py:156-191` - Core runtime loop for a round; each step calls `agent.handle()`, computes `next_state`/`next_agent`, and continues until terminal state.
- `ufo/agents/agent/host_agent.py:313-364` - Host agent’s key delegation point; chooses subagent type (app/operator/third-party) and instantiates worker agents dynamically.
- `ufo/client/computer.py:79-110,283-343,693-787` - Tool runtime: initializes MCP servers, registers tools, maps commands to tools, executes them, and returns standardized results.
- `galaxy/agents/constellation_agent.py:307-416` - LLM-facing DAG planner/editor logic; creates or edits the task constellation and synchronizes it back to tool layer.
- `galaxy/constellation/orchestrator/orchestrator.py:143-220,394-433,603-694` - Event-driven DAG executor; validates graph, schedules ready tasks asynchronously, and publishes task lifecycle events.

## 6. Use-Case Mapping

The repository does implement **Browser / Terminal Use** aspects indirectly through desktop/app automation and tool execution APIs, but its center of gravity is broader: it is primarily a **workflow orchestration platform** for multi-step, multi-device task graphs. UFO’s host/app structure automates desktop application workflows, while Galaxy explicitly builds and executes DAG workflows with assignment/synchronization logic (`ufo/agents/agent/host_agent.py:145-176`, `galaxy/session/galaxy_session.py:170-177`, `galaxy/constellation/orchestrator/orchestrator.py:151-179`). So the assigned category is partially valid, but **Workflow Automation** is the better top-level fit.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent decomposition (manager + workers + graph executor) with explicit state machines.
  - Strong tool abstraction via MCP (local/http/stdio) enabling extensible external capability injection.
  - Practical asynchronous DAG execution with readiness scheduling and event publication.
  - Built-in observability hooks (observers, trajectories, screenshots/UI trees, metrics).
  - Supports heterogeneous LLM providers with fallback path.

- **Limitations:**
  - Architecture is complex and split between legacy UFO and newer Galaxy paths, increasing cognitive overhead.
  - Several broad `except Exception` blocks reduce failure transparency and can mask root causes.
  - Heavy reliance on mutable shared context/state may be error-prone under concurrency.
  - Some operator/advanced paths appear partially stubbed or less mature than core flows.
  - Tight coupling to MCP/tool availability; missing/invalid tool config can break runtime early.

- **Research relevance:**
  - Evidence of a production-style **hybrid MAS pattern**: hierarchical delegation plus event-driven graph execution.
  - Useful case study for **LLM-planned DAG adaptation** during execution (constellation editing/synchronization).
  - Demonstrates an agent-tool interface layer (MCP) for grounding LLM decisions into executable actions.
  - Relevant for studying observability and control in real-world agentic workflow systems.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
