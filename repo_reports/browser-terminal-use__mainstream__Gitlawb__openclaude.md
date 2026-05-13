---
repo_name: Gitlawb/openclaude
url: "https://github.com/Gitlawb/openclaude"
stars: 23788
forks: 7878
contributors_count: 89
last_commit_date: "2026-04-22T17:37:02+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:38:23.894554+00:00"
model: auto
duration_s: 136.4
clone_size_kb: 28087
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`openclaude` is a TypeScript CLI coding agent that users run as `openclaude` to interact with LLMs that can read/write files, run shell commands, call web/MCP tools, and delegate work to subagents. In a normal session, the main agent loops through model responses and tool calls; in advanced sessions, it can spawn additional agents/teammates and coordinate them through tasks plus mailbox messaging. The project is not just a chat wrapper: it includes concrete runtime infrastructure for permissions, tool execution, transcript persistence, and background task management. Users effectively get an extensible autonomous coding workflow engine that can operate locally (terminal/filesystem) and across external services (MCP, web, remote-control channels).

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework**, not LangChain/LangGraph/CrewAI/AutoGen/LlamaIndex. The core runtime is hand-rolled around a `query()` loop and tool abstraction (`buildTool`), with custom agent spawning in `runAgent` (`src/tools/AgentTool/runAgent.ts:250-334`, `:762-771`) and tool registry assembly in `src/tools.ts:182-240`. `package.json` shows provider/MCP SDK dependencies but no LangChain/LangGraph-style framework imports (`package.json:70-148`).

Architecture is layered: (1) a primary interactive agent; (2) spawned subagents via `AgentTool`; and (3) optional swarm teammates (in-process or pane-backed) coordinated by team state + mailbox. Subagents are launched through `AgentTool.call()` and run through the shared `runAgent()` engine (`src/tools/AgentTool/AgentTool.tsx:239-301`, `src/tools/AgentTool/runAgent.ts:250-334`). Swarm teammates are created via `spawnTeammate()` and either run in-process (`spawnInProcessTeammate` + `runInProcessTeammate`) or out-of-process panes (`src/tools/shared/spawnMultiAgent.ts:905-1156`, `:376-612`).

“Intelligence” is concentrated in system prompts plus tool-enabled runtime loops, not in a static graph DSL. Teammates receive a specialized prompt addendum and run repeated prompt/idle cycles with mailbox polling and task claiming (`src/utils/swarm/inProcessRunner.ts:923-970`, `:1047-1176`, `:1353-1416`), while permission and policy constraints are enforced around tool calls.

## 3. Orchestration Pattern

Closest pattern: **hierarchical manager-worker**, with **event-driven mailbox coordination** layered on top.

The manager/leader uses `AgentTool` and team tools to spawn workers and dispatch work (`src/tools/AgentTool/AgentTool.tsx:282-301`, `src/tools/shared/spawnMultiAgent.ts:1151-1156`). Workers (teammates/subagents) execute independently and report via mailbox/task state.

Example control flow (spawn path):
- `if (teamName && name) { ... spawnTeammate(...) }` in `AgentTool` (`src/tools/AgentTool/AgentTool.tsx:282-301`)
- `spawnTeammate(...) -> handleSpawnInProcess/handleSpawnSplitPane` in shared spawner (`src/tools/shared/spawnMultiAgent.ts:1103-1141`)

Example event-driven loop (worker side):
- `while (!abortController.signal.aborted && !shouldExit) { ... runAgent(...) ... waitForNextPromptOrShutdown(...) }` (`src/utils/swarm/inProcessRunner.ts:1047-1050`, `:1175-1203`, `:1353-1361`)
- mailbox read/write primitives (`readMailbox`, `writeToMailbox`) provide asynchronous teammate signaling (`src/utils/teammateMailbox.ts:84-107`, `:134-192`).

## 4. Tools & External Integrations

- **Terminal/Shell execution**: `BashTool` executes commands, supports background tasks, sandbox checks, and command safety heuristics (`src/tools/BashTool/BashTool.tsx:14-51`, `:227-243`).  
- **PowerShell execution**: first-class Windows shell tool (`src/tools/PowerShellTool/PowerShellTool.tsx` via registry in `src/tools.ts:139-144`, `:230`).  
- **Filesystem editing/search**: read/edit/write/glob/grep/notebook tools are core built-ins (`src/tools.ts:5-10`, `:190-199`).  
- **MCP ecosystem**: MCP client transport and dynamic tool bridging (`stdio`, SSE, streamable HTTP, WebSocket) in `src/services/mcp/client.ts:7-21`, `:97-104`; generic MCP tool wrapper in `src/tools/MCPTool/MCPTool.ts:58-87`; MCP resource listing/reading in `src/tools.ts:233-235`.  
- **Web retrieval/search**: `WebFetchTool` (HTTP + optional Firecrawl) (`src/tools/WebFetchTool/WebFetchTool.ts:24-37`, `:81-115`) and `WebSearchTool` (native/provider-adapter web search) (`src/tools/WebSearchTool/WebSearchTool.ts:32-38`, `:149-156`).  
- **Browser/computer-use integrations (feature-gated)**: optional `WebBrowserTool` in tool registry (`src/tools.ts:106-108`, `:204`) and MCP/browser bridges such as Claude-in-Chrome and computer-use hooks in MCP client/CLI (`src/services/mcp/client.ts:235-253`, `src/entrypoints/cli.tsx:173-193`).  
- **Remote peer/session messaging**: `SendMessageTool` supports teammate mailbox, UDS, and bridge session targets (`src/tools/SendMessageTool/SendMessageTool.ts:67-75`, `:741-798`).

## 5. Notable Code Walkthrough

- `src/tools/AgentTool/runAgent.ts:250-374, 661-733, 762-833` - Core agent execution generator. It composes prompts/context/tools, initializes agent-specific MCP servers, runs the query loop, streams messages, and handles cleanup.
- `src/tools/shared/spawnMultiAgent.ts:376-523, 905-1003, 1103-1156` - Unified teammate spawning backend. It chooses pane-backed vs in-process execution, injects teammate identity/flags, and starts persistent worker loops.
- `src/utils/swarm/inProcessRunner.ts:883-970, 1047-1203, 1353-1416` - Long-lived teammate runtime: iterative `runAgent` turns, compaction, permission mediation, mailbox polling, shutdown/message handling.
- `src/tools/SendMessageTool/SendMessageTool.ts:149-189, 191-266, 800-890` - Inter-agent communication layer (direct, broadcast, structured control messages, and auto-resume routing for agent targets).
- `src/services/mcp/client.ts:7-21, 97-104, 174-219` - MCP integration spine that creates client transports, connects servers, fetches tools, and manages MCP lifecycle/auth behavior.

## 6. Use-Case Mapping

This repository does implement the assigned **Browser / Terminal Use** category (strong terminal/tooling support), but its center of gravity is broader: **multi-agent workflow automation**. Terminal use is concrete and first-class (`BashTool`, `PowerShellTool`, filesystem tools), while browser/web capability is mostly via WebFetch/WebSearch and feature-gated browser/computer-use tooling. The multi-agent mechanics (team creation, spawn, mailbox routing, task claiming, plan approval/shutdown protocols) indicate that a better top-level label is **Workflow Automation** rather than pure browser/terminal interaction.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Implements real runtime multi-agent coordination (leader + teammates + subagents), not just prompt templates.
  - Supports multiple execution substrates (in-process AsyncLocalStorage, tmux/iTerm pane agents).
  - Strong tool ecosystem integration (MCP, shell, web, files) with permission and policy controls.
  - Robust lifecycle handling: background tasks, abort semantics, cleanup, transcript persistence.
  - Practical interoperability across many LLM providers/models through unified tool loop.

- **Limitations:**
  - Architecture is highly feature-flagged and sprawling, raising complexity for reproducibility and comprehension.
  - Workflow engine appears partially gated/stubbed in this snapshot (`WorkflowTool` constants-only source visible).
  - Heavy reliance on polling/file-mailbox semantics may introduce latency/race edge cases under high agent counts.
  - Browser automation is less explicit than terminal/shell orchestration unless optional gates/modules are enabled.
  - System behavior depends on runtime config/env, making “default” behavior harder to infer from static code alone.

- **Research relevance:**
  - Good evidence of production-grade **hierarchical MAS orchestration** with tool-using LLM workers.
  - Useful case for studying **permission mediation and safety policies** in multi-agent tool execution.
  - Demonstrates hybrid coordination primitives: shared state + message passing + task queues.
  - Illustrates engineering tradeoffs between in-process agents and process/pane-isolated workers.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
