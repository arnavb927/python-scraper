---
repo_name: infiniflow/ragflow
url: "https://github.com/infiniflow/ragflow"
stars: 78786
forks: 8903
contributors_count: 535
last_commit_date: "2026-04-23T03:40:45+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T10:07:29.073500+00:00"
model: auto
duration_s: 108.1
clone_size_kb: 124105
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`infiniflow/ragflow` is a full-stack RAG platform where users build and run visual “agent canvases” (DSL graphs) that combine LLM reasoning, retrieval, and tool execution. In practice, a user creates an agent workflow in the web UI, then runs it through API/session endpoints that stream node-level events and model output (`api/apps/restful_apis/agent_api.py:848-1055`). Under the hood, the backend executes a custom graph runtime (`agent/canvas.py`) that routes data between components such as `Agent`, `LLM`, `Retrieval`, `Invoke`, loops, switches, and message nodes. The output is a runnable assistant or automation flow that can answer questions, call external tools/APIs, execute code, and return citations/references.

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework**, not LangGraph/CrewAI/AutoGen/LangChain as primary orchestration. The core runtime is `Canvas(Graph)` and component classes dynamically loaded from `agent.component`, `agent.tools`, and `rag.flow` (`agent/component/__init__.py:51-58`, `agent/canvas.py:84-111`). Tool calling is implemented via an in-house `ToolCallSession` abstraction (`agent/tools/base.py:50-74`) bound into their LLM wrapper (`agent/component/agent_with_tools.py:107-111`).

Architecture-wise, each workflow is a DSL graph of nodes (`components`, `upstream`, `downstream`, `path`) executed by `Canvas.run()` (`agent/canvas.py:43-81`, `agent/canvas.py:377-660`). “Intelligence” primarily lives in:
- Node prompts (`sys_prompt`, multi-role task instructions) in Agent/LLM components and templates (`agent/templates/deep_research.json`),
- Dynamic path routing logic in `Canvas.run()` for switch/categorize/loop/iteration nodes (`agent/canvas.py:616-630`),
- Tool-use binding where `Agent` nodes expose tools (including nested `Agent` tools and MCP tools) to the model (`agent/component/agent_with_tools.py:79-111`).

It also supports explicit multi-agent setups: `Agent` is itself a `ToolBase`, so one agent can call other agents as tools (manager-worker style), and templates like `deep_research` define “Strategy Research Director” plus specialized subordinate agents (`agent/templates/deep_research.json` matches at lines around 21, 56, 58, 132, 185).

## 3. Orchestration Pattern

Closest match: **graph/state-machine orchestration with hierarchical manager-worker behavior inside nodes**.

The top-level control flow is graph-driven: `Canvas.run()` iterates through `self.path`, executes ready nodes, then appends downstream nodes conditionally by component type (`switch`, `categorize`, `loop`, `iteration`, etc.):

```397:630:agent/canvas.py
for i in range(idx, to):
    ...
await _run_batch(idx, to)
...
if cpn_obj.component_name.lower() in ["categorize", "switch"]:
    _extend_path(cpn_obj.output("_next"))
elif cpn_obj.component_name.lower() in ("iteration", "loop"):
    _append_path(cpn_obj.get_start())
...
else:
    _extend_path(cpn["downstream"])
```

Inside an `Agent` node, orchestration is hierarchical/tool-mediated: the LLM is bound to tool metadata and can invoke indexed tools (including nested agents and MCP tools), with callback trace capture:

```79:111:agent/component/agent_with_tools.py
for idx, cpn in enumerate(self._param.tools):
    cpn = self._load_tool_obj(cpn)
    indexed_name = f"{original_name}_{idx}"
    self.tools[indexed_name] = cpn
...
self.toolcall_session = LLMToolPluginCallSession(self.tools, self.callback)
if self.tool_meta:
    self.chat_mdl.bind_tools(self.toolcall_session, self.tool_meta)
```

## 4. Tools & External Integrations

- **LLM model providers (chat/embedding/rerank/TTS/image2text)**: wrapped via `LLMBundle` and tenant model configs (`agent/component/llm.py:88-92`, `agent/tools/retrieval.py:124-131`, `agent/canvas.py:520-522`).
- **MCP servers/tools**: MCP sessions over SSE/streamable HTTP with dynamic tool listing/calling (`common/mcp_tool_call_conn.py:42-120`, `common/mcp_tool_call_conn.py:177-230`), wired into Agent tools (`agent/component/agent_with_tools.py:100-107`).
- **RAG retrieval over internal datasets/memory + KG retrieval**: `Retrieval` tool calls platform retriever and adds references (`agent/tools/retrieval.py:189-202`, `agent/tools/retrieval.py:257-264`).
- **Web search and extraction APIs**: Tavily (`agent/tools/tavily.py:20-21`, `agent/tools/tavily.py:113-135`), plus other search tool modules in `agent/tools/` (DuckDuckGo, Google, SearXNG, etc.).
- **Web crawling**: Crawl4AI-based crawler (`agent/tools/crawler.py:18`, `agent/tools/crawler.py:64-76`).
- **Code execution sandbox**: provider-based or HTTP fallback sandbox (`agent/tools/code_exec.py:359-377`, `agent/tools/code_exec.py:398-414`), artifact upload/parsing support (`agent/tools/code_exec.py:518-548`, `agent/tools/code_exec.py:586-647`).
- **SQL/database execution**: MySQL/Postgres/MSSQL/DB2/Trino/OceanBase in `ExeSQL` (`agent/tools/exesql.py:127-145`, `agent/tools/exesql.py:172-183`, `agent/tools/exesql.py:240-289`).
- **Generic HTTP API invocation**: `Invoke` component for templated GET/POST/PUT requests (`agent/component/invoke.py:189-207`, `agent/component/invoke.py:217-246`).
- **Session/runtime API + SSE streaming**: agent execution endpoints and OpenAI-compatible mode (`api/apps/restful_apis/agent_api.py:848-927`, `api/apps/restful_apis/agent_api.py:984-1025`).
- **Webhook execution mode with security controls**: auth/rate-limit/IP checks and async execution (`api/apps/restful_apis/agent_api.py:1058-1130`, `api/apps/restful_apis/agent_api.py:1582-1663`).

## 5. Notable Code Walkthrough

- `agent/canvas.py:377-660` — Core graph runtime. Executes node batches asynchronously, emits workflow/node/message events, handles branching/loops/user-fill-up checkpoints, and appends downstream paths dynamically.
- `agent/component/agent_with_tools.py:73-111` — Main “agentic” node. Builds tool registry, binds tool schemas to LLM, and supports MCP + nested tool components (including agent-as-tool delegation).
- `agent/tools/base.py:50-74` — Unified tool-call session abstraction. Dispatches synchronous/async/MCP tool calls, records elapsed time, and sends trace callbacks used by UI/debug logs.
- `common/mcp_tool_call_conn.py:42-120` — MCP transport implementation. Maintains background event loop/thread, initializes MCP client sessions, and processes queued list-tools/tool-call tasks.
- `api/apps/restful_apis/agent_api.py:929-1015` — Runtime execution entrypoint for draft agent runs; loads canvas replica, runs `Canvas.run()` as SSE stream, and commits updated runtime state.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only a partial fit. This codebase does include web interaction capabilities (crawler, web search/extract APIs, webhook/http invoke), but it is **not primarily a browser automation or terminal-control agent framework** (no Playwright-style agent loop, shell-agent core, or autonomous terminal planner as the main product).

The strongest fit from the provided taxonomy is **Workflow Automation** (with heavy **RAG + Agents** characteristics). The central artifact is a visual, executable workflow graph with conditional routing, loops, external tools, and streaming runtime events (`agent/canvas.py`, `agent_api.py`), which is broader than browser/terminal usage.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Custom graph runtime supports nontrivial control flow (branching, loops, iteration, human fill-up checkpoints) instead of linear chains (`agent/canvas.py:616-650`).
  - Practical multi-agent composition via agent-as-tool and rich template library (e.g., deep research manager/specialist decomposition).
  - Strong integration surface: MCP, retrieval, SQL, web APIs, web crawl, sandboxed code execution.
  - Production-oriented observability through streamed node events and per-tool trace logs (`agent/canvas.py:787-807`, `agent_api.py:240-268`).
  - Multi-tenant model abstraction and configurable model backends through `LLMBundle`.

- **Limitations:**
  - Multi-agent behavior is mostly prompt-convention + tool-calling, not a formally typed planner/critic protocol with strict contracts between agents.
  - Orchestration logic is complex and centralized in `Canvas.run()`, which may be hard to verify formally and maintain.
  - Some heavy reliance on dynamic DSL and runtime mutation can complicate static analysis and reproducibility.
  - Several tool wrappers are synchronous/thread-offloaded; failure modes and retries vary per tool implementation.
  - “Agent framework” capabilities are tightly coupled to platform services (tenant config, DB models, Redis state), reducing portability.

- **Research relevance:**
  - Evidence of **applied multi-agent orchestration in production** using manager-worker decomposition inside workflow graphs.
  - Useful case for studying **tool-augmented LLM agents with heterogeneous tool backends** (MCP + custom tools + RAG).
  - Demonstrates a hybrid architecture: **graph-based process control + LLM-level autonomous tool choice**.
  - Relevant to human-in-the-loop studies via pause/resume and user-input nodes (`userfillup`) in graph execution.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
