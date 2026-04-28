---
repo_name: gsd-build/gsd-2
url: "https://github.com/gsd-build/gsd-2"
stars: 6435
forks: 659
contributors_count: 88
last_commit_date: "2026-04-23T01:53:12+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T11:27:30.629825+00:00"
model: auto
duration_s: 104.5
clone_size_kb: 37030
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`gsd-2` is a TypeScript-based autonomous coding agent platform that users run as a CLI (`gsd`) with interactive, print, or RPC modes, and optional web/VSCode integrations (`packages/pi-coding-agent/src/main.ts:1-33`, `packages/pi-coding-agent/src/main.ts:613-648`). At runtime it builds an `AgentSession` with a model, system prompt, tools, extension hooks, persistence, retry, and compaction controls (`packages/pi-coding-agent/src/core/sdk.ts:231-566`, `packages/pi-coding-agent/src/core/agent-session.ts:1-14`). The core loop streams LLM responses, executes tool calls, feeds tool results back, and repeats until stop (`packages/pi-agent-core/src/agent-loop.ts:175-398`). Beyond a single coding agent, it also supports delegating work to specialized subagents (single, parallel, chain) via a dedicated `subagent` tool (`src/resources/extensions/subagent/index.ts:1-13`, `src/resources/extensions/subagent/index.ts:654-676`).

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen as its runtime framework. The implementation is a **custom agent stack** built around internal packages `@gsd/pi-agent-core`, `@gsd/pi-coding-agent`, and `@gsd/pi-ai` (`packages/pi-agent-core/src/agent.ts:6-18`, `packages/pi-coding-agent/src/core/sdk.ts:41-49`). A search for common external orchestration frameworks finds no real runtime imports, only incidental text mentions (`rg` results; no LangGraph/CrewAI runtime imports in core files).

Architecture is layered. `Agent` in `pi-agent-core` manages model state, queues (steering/follow-up), and loop execution (`packages/pi-agent-core/src/agent.ts:130-180`, `packages/pi-agent-core/src/agent.ts:475-532`). `agentLoop` is the execution kernel: stream assistant output, parse tool calls, run tools (sequential/parallel), append tool results, and continue (`packages/pi-agent-core/src/agent-loop.ts:263-317`, `packages/pi-agent-core/src/agent-loop.ts:517-657`). `AgentSession` in `pi-coding-agent` wraps this with persistent sessions, extension event bus, tool registry, retries/fallbacks, and compaction (`packages/pi-coding-agent/src/core/agent-session.ts:235-360`, `packages/pi-coding-agent/src/core/agent-session.ts:492-534`).

The “intelligence” is distributed across model prompts/context transforms, tool schemas, and extension-provided prompt guidance. Extensions can register tools, commands, prompt snippets/guidelines, and context transforms that affect behavior per turn (`packages/pi-coding-agent/src/core/agent-session.ts:2151-2213`, `packages/pi-coding-agent/src/core/agent-session.ts:2062-2148`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker**, with an embedded **iterative tool loop**.

- The primary agent behaves as manager/controller: it asks the model, dispatches tool calls, consumes results, and re-prompts until completion (`packages/pi-agent-core/src/agent-loop.ts:193-205`, `packages/pi-agent-core/src/agent-loop.ts:509-520`).
- Multi-agent behavior is explicit in the `subagent` tool, where a parent agent delegates tasks to child agent processes in **single**, **parallel**, or **chain** modes (`src/resources/extensions/subagent/index.ts:7-11`, `src/resources/extensions/subagent/index.ts:877-933`, `src/resources/extensions/subagent/index.ts:935-1056`).

Control flow excerpt 1 (main loop + tool recursion):
`packages/pi-agent-core/src/agent-loop.ts:263-271`
```ts
const toolCalls = message.content.filter((c) => c.type === "toolCall");
hasMoreToolCalls =
  toolCalls.length > 0 || message.stopReason === "pauseTurn";
...
const toolExecution = await executeToolCalls(...)
```

Control flow excerpt 2 (manager delegating to parallel subagents):
`src/resources/extensions/subagent/index.ts:986-994`
```ts
const results = await mapWithConcurrencyLimit(params.tasks, MAX_CONCURRENCY, async (t, index) => {
  const workerId = registerWorker(t.agent, t.task, index, batchSize, batchId);
  const runTask = () => ... runSingleAgentInCmuxSplit(...) : runSingleAgent(...);
```

## 4. Tools & External Integrations

- **Local coding/file tools** (`read`, `bash`, `edit`, `write`, etc.) wired as base tools and activated in session runtime (`packages/pi-coding-agent/src/core/agent-session.ts:2222-2234`, `packages/pi-coding-agent/src/core/agent-session.ts:2265-2273`).
- **Shell/terminal execution** via `bash` tool using spawned shell processes, timeout/streaming/interception logic (`packages/pi-coding-agent/src/core/tools/bash.ts:111-146`, `packages/pi-coding-agent/src/core/tools/bash.ts:151-170`).
- **Filesystem reading + image ingestion** via `read` tool (text truncation, image MIME detect/resize) (`packages/pi-coding-agent/src/core/tools/read.ts:49-57`, `packages/pi-coding-agent/src/core/tools/read.ts:102-131`).
- **MCP client integration**: discovers server configs (`.mcp.json`, `.gsd/mcp.json`, `~/.gsd/mcp.json`), connects via stdio/HTTP MCP transports, exposes `mcp_servers`, `mcp_discover`, `mcp_call` tools (`src/resources/extensions/mcp-client/index.ts:4-13`, `src/resources/extensions/mcp-client/index.ts:104-109`, `src/resources/extensions/mcp-client/index.ts:383-433`, `src/resources/extensions/mcp-client/index.ts:520-557`).
- **Web search stack** with Brave/Tavily/Ollama providers and cached search/fetch/context tools via extension loading (`src/resources/extensions/search-the-web/index.ts:15-31`, `src/resources/extensions/search-the-web/tool-search.ts:19-25`, `src/resources/extensions/search-the-web/tool-search.ts:103-127`).
- **Subprocess-based multi-agent delegation** (`subagent`) spawning separate CLI processes with isolated context windows (`src/resources/extensions/subagent/index.ts:4-5`, `src/resources/extensions/subagent/index.ts:407-414`).
- **Task isolation via git worktree/fuse-overlay** for delegated runs and patch merge-back (`src/resources/extensions/subagent/isolation.ts:21-44`, `src/resources/extensions/subagent/isolation.ts:123-157`, `src/resources/extensions/subagent/isolation.ts:198-204`).
- **Standalone MCP server package** exposing orchestration/workflow/project-state tools for external MCP clients (`packages/mcp-server/src/server.ts:2-8`, `packages/mcp-server/src/server.ts:28-30`).

## 5. Notable Code Walkthrough

- `packages/pi-agent-core/src/agent-loop.ts:89-119,175-398,509-657` - Core event-driven LLM/tool loop; handles streaming, tool dispatch (sequential/parallel), steering/follow-up messages, and termination/error caps.
- `packages/pi-coding-agent/src/core/agent-session.ts:303-360,2062-2148,2151-2273` - Session orchestrator that binds extension runtime, merges tool registries, persists conversation/events, and injects extension hooks around each turn.
- `packages/pi-coding-agent/src/core/sdk.ts:231-341,382-417,546-565` - Factory that assembles model/auth/settings/resource loaders and returns a fully wired `AgentSession`; this is the practical runtime entry for the CLI.
- `src/resources/extensions/subagent/index.ts:654-676,877-933,935-1056,1058-1124` - Multi-agent delegation tool implementing single/chain/parallel dispatch, retries, telemetry, and optional isolated execution.
- `src/resources/extensions/mcp-client/index.ts:99-159,235-302,383-433,522-583` - MCP integration layer that reads server config, manages lazy connections, and exposes generic MCP discovery/call tools to the agent.

## 6. Use-Case Mapping

Although this project is strongly used for coding tasks, the codebase itself implements a broader **agent orchestration runtime**: session lifecycle management, tool ecosystems, extension events, MCP client/server interop, retries/compaction, and delegated subagent workflows (`packages/pi-coding-agent/src/core/agent-session.ts:1-14`, `src/resources/extensions/subagent/index.ts:7-11`, `packages/mcp-server/src/server.ts:2-8`). So the assigned “Code Generation” label is partially true at UX level, but at architecture level the better fit is **Workflow Automation** with code generation as a major domain specialization.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong custom orchestration kernel with explicit event types and robust loop controls (streaming, retries, validation-failure caps) (`packages/pi-agent-core/src/agent-loop.ts:32-33`, `packages/pi-agent-core/src/agent-loop.ts:324-370`).
  - Real runtime multi-agent support (subprocess subagents, chain + parallel execution) rather than prompt-only roleplay (`src/resources/extensions/subagent/index.ts:7-11`, `src/resources/extensions/subagent/index.ts:935-1056`).
  - Highly extensible tool/command architecture via `ExtensionRunner` and runtime tool registry refresh (`packages/pi-coding-agent/src/core/agent-session.ts:2151-2213`, `packages/pi-coding-agent/src/core/agent-session.ts:2245-2263`).
  - First-class MCP interoperability on both client and server sides (`src/resources/extensions/mcp-client/index.ts:24-26`, `packages/mcp-server/src/server.ts:35-38`).
  - Practical engineering safeguards: auth cooldown logic, compaction, queue semantics, and image overflow recovery (`packages/pi-coding-agent/src/core/sdk.ts:417-529`, `packages/pi-coding-agent/src/core/agent-session.ts:503-529`).

- **Limitations:**
  - Subagent parallelism is process-based and operationally heavy (spawning full CLI processes), which may increase latency and resource usage (`src/resources/extensions/subagent/index.ts:410-414`).
  - Multi-agent coordination appears centralized in one parent session rather than decentralized peer negotiation/swarm memory.
  - Large monolithic orchestration files (e.g., `agent-session.ts`, `subagent/index.ts`) raise complexity and maintenance burden.
  - Isolation merge path relies on patch application; conflicts/non-clean applies can degrade reliability in complex repos (`src/resources/extensions/subagent/isolation.ts:164-185`).
  - Framework-specific abstractions are custom; portability to standard graph-based ecosystems may require adaptation.

- **Research relevance:**
  - Evidence of a production-grade **manager-worker MAS** with explicit delegation policies (single/chain/parallel) and structured telemetry (`src/resources/extensions/subagent/index.ts:715-751`, `src/resources/extensions/subagent/index.ts:821-847`).
  - Useful case study for event-sourced agent runtimes integrating local tools + MCP + web retrieval.
  - Demonstrates guardrail patterns for long-running autonomous agents: retry/cooldown/compaction/overflow recovery.
  - Illustrates extension-driven agent capability composition in a live developer tooling context.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
