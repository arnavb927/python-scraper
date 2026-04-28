---
repo_name: microsoft/magentic-ui
url: "https://github.com/microsoft/magentic-ui"
stars: 9786
forks: 974
contributors_count: 30
last_commit_date: "2026-02-12T16:08:52+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 9
architecture_labels: [AutoGen, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T09:18:14.562760+00:00"
model: auto
duration_s: 74.0
clone_size_kb: 11939
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`microsoft/magentic-ui` is a Python + FastAPI application that runs a human-in-the-loop multi-agent assistant focused on completing real tasks through a browser, local files, code execution, and optional MCP tools. A user typically launches `magentic-ui`, opens the web UI, and submits a task; the backend then constructs an agent team and streams planning/execution updates. The system’s orchestrator creates and revises plans, routes instructions to specialized agents (web, code, files, MCP), and synthesizes a final answer. In practice, users get an interactive agent workflow with visible step-by-step actions, approvals, and generated artifacts.

## 2. Agent Framework & Architecture

The framework is **AutoGen (AgentChat + Core + Ext)**, not LangGraph/CrewAI. This is explicit in dependencies and imports such as `autogen-agentchat`, `autogen-core`, `autogen-ext` (`pyproject.toml:27-31`) and team/agent classes derived from AutoGen abstractions (`src/magentic_ui/teams/orchestrator/_group_chat.py:17-24`, `src/magentic_ui/agents/_coder.py:21-37`).

Architecture is a **custom orchestrated multi-agent team** built on AutoGen group chat primitives. Team assembly happens in `get_task_team()`, which instantiates `WebSurfer`, `CoderAgent`, `FileSurfer`, optional `McpAgent`s, and a user proxy, then wraps them in a custom `GroupChat` with an `Orchestrator` manager (`src/magentic_ui/task_team.py:34-39`, `:249-264`). The orchestrator holds conversation state, plan state, step index, replanning counters, and memory integration (`src/magentic_ui/teams/orchestrator/_orchestrator.py:70-87`, `:171-188`).

“Intelligence” lives in three places: (1) orchestrator prompts/JSON ledgers for planning and routing (`_orchestrator.py:253-341`, `:977-989`), (2) specialist-agent prompting and tool loops (e.g., web tool-calling loop in `_web_surfer.py:614-676`, `:1230-1272`), and (3) optional memory/Bing augmentation during planning (`_orchestrator.py:590-610`, `:673-707`).

## 3. Orchestration Pattern

Closest pattern: **hierarchical manager-worker (with state-machine-like phases)**.

The orchestrator alternates between planning and execution modes and delegates each step to a chosen specialist agent. Control switching is explicit:

```826:942:src/magentic_ui/teams/orchestrator/_orchestrator.py
if self._state.in_planning_mode:
    await self._orchestrate_step_planning(cancellation_token)
else:
    await self._orchestrate_step_execution(cancellation_token)
...
self._state.in_planning_mode = False
await self._orchestrate_step_execution(cancellation_token, first_step=True)
```

In execution, it uses an LLM-generated progress ledger to pick the next agent and sends `GroupChatRequestPublish` to that participant:

```977:1082:src/magentic_ui/teams/orchestrator/_orchestrator.py
progress_ledger = await self._get_json_response(...)
next_speaker = progress_ledger["instruction_or_question"]["agent_name"]
for participant_name in self._agent_execution_names:
    if participant_name == next_speaker:
        await self._request_next_speaker(next_speaker, cancellation_token)
        valid_next_speaker = True
        break
```

There is also a simplified alternative mode (`websurfer_loop`) using pure round-robin turns (`src/magentic_ui/task_team.py:202-208`, `src/magentic_ui/teams/roundrobin_orchestrator.py:125-144`), but the default runtime is orchestrator-led hierarchy.

## 4. Tools & External Integrations

- **Browser automation (Playwright)**: Web agent wraps Playwright browser/context/page operations and executes tool calls like `visit_url`, `click`, `input_text`, `scroll`, tabs (`src/magentic_ui/agents/web_surfer/_web_surfer.py:331-358`, `:1348-1805`; controller in `src/magentic_ui/tools/playwright/playwright_controller.py`).
- **Containerized/local code execution**: `CoderAgent` executes generated code via Docker or local command-line executors (`src/magentic_ui/agents/_coder.py:36-37`, `:404-416`, `:514-523`).
- **Filesystem reading/navigation agent**: `FileSurfer` exposes tools to open/list/find files and paginate content, backed by a markdown file browser + executor (`src/magentic_ui/agents/file_surfer/_file_surfer.py:166-174`, `:405-507`).
- **MCP servers/tools**: `McpAgent` uses `AggregateMcpWorkbench` to connect multiple MCP servers and namespace tools (`src/magentic_ui/agents/mcp/_agent.py:50-53`, `src/magentic_ui/tools/mcp/_aggregate_workbench.py:130-169`).
- **Web search enrichment (Bing)**: Orchestrator can call a Bing-search helper during planning, which scrapes results/pages via Playwright (`src/magentic_ui/teams/orchestrator/_orchestrator.py:590-603`, `src/magentic_ui/tools/bing_search.py:60-77`).
- **FastAPI + WebSocket UI backend**: UI/API app wires team execution endpoints and streaming routes (`src/magentic_ui/backend/web/app.py:113-167`).

## 5. Notable Code Walkthrough

- `src/magentic_ui/task_team.py:34-266` - Central team factory that wires model clients, browser config, approval guard, agent roster, memory provider, and final `GroupChat`/`RoundRobinGroupChat`.
- `src/magentic_ui/teams/orchestrator/_orchestrator.py:113-1768` - Core manager logic: planning prompts, JSON validation/retries, execution routing, replanning, sentinel steps, and final answer synthesis.
- `src/magentic_ui/agents/web_surfer/_web_surfer.py:160-2151` - Browser specialist implementing multimodal context construction, tool-selection loop, Playwright action execution, URL approvals, screenshots, and page QA.
- `src/magentic_ui/agents/_coder.py:92-250` - Code-writing/debugging loop where LLM outputs code blocks, executor runs them, and results are fed back for iterative repair.
- `src/magentic_ui/tools/mcp/_aggregate_workbench.py:55-169` - Multi-server MCP abstraction that namespaces tool schemas and dispatches calls to the correct server.

## 6. Use-Case Mapping

This repository strongly realizes **Browser / Terminal Use**: the web agent actively controls a real browser (navigation, DOM interaction, tab management, screenshots, page summarization) (`src/magentic_ui/agents/web_surfer/_web_surfer.py:165-177`, `:1348-1703`). It also includes “terminal-like” execution via coder/file agents using local/docker command execution and filesystem tooling (`src/magentic_ui/agents/_coder.py:319-333`, `src/magentic_ui/agents/file_surfer/_file_surfer.py:113-126`). The orchestrator converts user goals into delegated execution steps across these capabilities (`src/magentic_ui/teams/orchestrator/_orchestrator.py:943-1082`).  

The assigned primary use case looks correct; if anything, it secondarily overlaps with Workflow Automation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Explicit multi-agent specialization (web/code/files/MCP) with a manager that routes by plan step.
  - Strong observability: streamed progress, checkpoint state emission, metadata-tagged events (`_group_chat.py:115-128`).
  - Human-centered controls: approval guard for risky actions and URL/domain permission gates (`_web_surfer.py:688-729`, `:1314-1341`).
  - Practical tool depth: real Playwright control plus MCP ecosystem interoperability.
  - Replanning and sentinel-step support for long-running/monitoring workflows (`_orchestrator.py:1119-1195`, `:1344-1768`).

- **Limitations:**
  - Heavy complexity and many async branches make correctness/testing difficult; orchestrator is very large and monolithic.
  - Bing planning augmentation is brittle/resource-heavy (multiple ad-hoc browser spawns) (`tools/bing_search.py:68-69`, `:146-149`).
  - Some fallback/error paths are permissive (`except Exception ... pass`) which can hide failures (`_orchestrator.py:669-671`).
  - Tool use safety depends on policy/runtime approval choices; autonomous paths can still be high-impact.
  - Strong coupling to AutoGen internals/events may make framework migration expensive.

- **Research relevance:**
  - Concrete evidence of hierarchical LLM orchestration with planner/executor separation in production-like code.
  - Useful case study for human-in-the-loop governance (approvals + constrained browsing) in agent systems.
  - Demonstrates multimodal browser-state grounding (text + screenshots + UI element maps) for web agents.
  - Illustrates multi-tool/multi-agent integration (MCP + browser + code + files) under one orchestrator.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
