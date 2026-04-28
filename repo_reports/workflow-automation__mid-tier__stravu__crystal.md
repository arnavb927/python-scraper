---
repo_name: stravu/crystal
url: "https://github.com/stravu/crystal"
stars: 3032
forks: 194
contributors_count: 15
last_commit_date: "2026-02-26T21:44:09+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T14:54:35.740262+00:00"
model: auto
duration_s: 82.8
clone_size_kb: 15664
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`stravu/crystal` is an Electron desktop app for running multiple AI coding sessions (Claude Code and Codex CLI) in parallel, each isolated in its own git worktree. A user creates one or more sessions from the UI, Crystal provisions worktrees, launches CLI agent processes in PTYs, streams structured output back into panel views, and persists everything in SQLite. It also adds workflow glue around session lifecycle, prompt history, git operations (rebase/merge/squash), and panel-level continuation/resume. In practice, users run Crystal to automate and compare multiple AI-assisted implementation workflows against the same repository.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex; it is a **custom orchestration layer** over external CLI agents. There are no framework imports for those stacks, and agent execution is delegated to CLI tools via PTY managers (`main/src/services/panels/cli/AbstractCliManager.ts:64-131`, `main/src/services/panels/claude/claudeCodeManager.ts:45-73`, `main/src/services/panels/codex/codexManager.ts:82-101`).

Architecture-wise, Crystal has:
- a generic CLI runtime abstraction (`AbstractCliManager`) that spawns/monitors tool processes and normalizes output events,
- tool-specific managers (`ClaudeCodeManager`, `CodexManager`) that build command args, parse JSON streams, and handle resume/session IDs,
- AI panel managers that bind runtime events to panel/session persistence (`AbstractAIPanelManager`),
- IPC handlers that route user actions to the right panel/tool and maintain app state (`main/src/ipc/session.ts`).

The “intelligence” (planning/problem-solving) mostly lives in the **external agents** (Claude Code / Codex), while Crystal provides deterministic control plane logic: session creation, tool routing, prompt/state persistence, permissions plumbing, and git/worktree workflow automation.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker orchestration** (not multi-agent collaboration). Crystal acts as a manager/control-plane; each Claude/Codex process is an independent worker tied to a panel/worktree. It supports many workers in parallel, but they are not coordinating with each other at runtime.

Control flow example (manager delegates to tool-specific panel worker):
```381:399:main/src/services/taskQueue.ts
const resolvedToolType: 'claude' | 'codex' | 'none' = toolType || 'claude';
...
if (resolvedToolType === 'codex') {
  ...
  await codexPanelManager.startPanel(...);
} else if (resolvedToolType === 'claude') {
  ...
  await claudePanelManager.startPanel(...);
}
```

Event-driven worker output routing back to storage/UI:
```61:73:main/src/services/panels/ai/AbstractAIPanelManager.ts
this.cliManager.on('output', (data) => {
  const { panelId } = data;
  if (panelId && this.panelMappings.has(panelId)) {
    this.sessionManager.addPanelOutput(panelId, {
      type: data.type as 'json' | 'stdout' | 'stderr' | 'error',
      data: data.data,
      timestamp: data.timestamp || new Date()
    });
  }
});
```

## 4. Tools & External Integrations

- **Claude Code CLI** (`claude` executable)  
  Wired in `main/src/services/panels/claude/claudeCodeManager.ts:65-152`, spawned via PTY in `main/src/services/panels/cli/AbstractCliManager.ts:169-185`.
- **OpenAI Codex CLI** (`codex exec --json`)  
  Wired in `main/src/services/panels/codex/codexManager.ts:192-261`, env/API keys in `:519-549`.
- **PTY process management (`node-pty`)** for interactive agent/runtime sessions  
  `main/src/services/panels/cli/AbstractCliManager.ts:2,555-657`.
- **MCP (Model Context Protocol) permission server/bridge** for tool approval flow  
  MCP server: `main/src/services/mcpPermissionServer.ts:1-89`; bridge subprocess: `main/src/services/mcpPermissionBridge.ts:6-167`; Claude MCP config wiring: `main/src/services/panels/claude/claudeCodeManager.ts:672-860`.
- **Git + git worktrees** for isolation and merge automation  
  Worktree lifecycle and rebase/merge logic in `main/src/services/worktreeManager.ts:72-176`, `:472-715`, `:717-809`.
- **SQLite persistence (`better-sqlite3`)** for sessions/outputs/conversation/panels  
  Used through `SessionManager` methods such as `main/src/services/sessionManager.ts:580-737`, `:852-1032`.
- **Task queueing (Bull or in-memory SimpleQueue)** for queued session creation/continuation  
  `main/src/services/taskQueue.ts:65-119`, `:148-423`.
- **Stravu API integration (not core orchestration but external service)**  
  Notebook endpoints in `main/src/services/stravuNotebookService.ts:56-125`, auth in `main/src/services/stravuAuthManager.ts:75-198`.

## 5. Notable Code Walkthrough

- `main/src/services/panels/cli/AbstractCliManager.ts:64-201,555-740`  
  Core engine for launching CLI agents, parsing line-buffered output, handling process lifecycle, and emitting normalized events consumed by panel/session layers.
- `main/src/services/panels/claude/claudeCodeManager.ts:65-152,346-443,672-860`  
  Claude-specific command construction, resume semantics, and MCP permission/config generation; this is the main adapter between Crystal and Claude Code.
- `main/src/services/panels/codex/codexManager.ts:192-261,356-517,936-1062`  
  Codex command setup and JSON stream parsing, including extraction/persistence of Codex session IDs for resume continuity.
- `main/src/services/taskQueue.ts:148-423,485-564`  
  Session orchestration pipeline: create worktree, create DB session, ensure panels, optionally run build script, and start the selected AI tool.
- `main/src/ipc/session.ts:113-179,329-499,1082-1217`  
  High-level orchestration entrypoints from UI actions; routes input/continue/create operations to panel managers and enforces tool-type-specific behavior.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. Crystal automates end-to-end AI development workflows: batch session creation, git-worktree isolation, tool startup, prompt persistence, continuation/resume, build/test hooks, and merge/rebase operations (`main/src/services/taskQueue.ts`, `main/src/services/worktreeManager.ts`, `main/src/ipc/session.ts`). It is not primarily a model-building framework or RAG system; it is an orchestration product for parallel AI-assisted coding operations.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Robust, production-style control plane around external agents (queueing, retries, lifecycle, state persistence).
  - Strong git/worktree automation for parallel experimentation and safe integration.
  - Unified abstraction for multiple CLI agents via `AbstractCliManager` + panel managers.
  - Practical MCP permission mediation for safer tool calls in agent sessions.
  - Rich panel/session telemetry persistence enabling reproducibility and post-hoc analysis.

- **Limitations:**
  - No intrinsic multi-agent reasoning topology (no planner-worker team or agent-agent messaging graph).
  - Coordination is mostly user/UI-driven; “parallel sessions” are independent rather than collaborative at runtime.
  - Heavy reliance on external CLI behavior/contracts (output schemas/session-id formats can drift).
  - Some orchestration paths include fallback/legacy branches, increasing complexity in control flow.
  - Little evidence of formal policy/verification logic for cross-agent task decomposition.

- **Research relevance:**
  - Strong evidence of **agent operations engineering** (runtime supervision, stateful orchestration, governance) rather than MAS cognition.
  - Useful case study for comparing “multi-session orchestration” vs true multi-agent collaboration.
  - Demonstrates practical MCP-based permission mediation in desktop agent tooling.
  - Relevant for studies on human-in-the-loop orchestration of multiple coding agents across isolated environments.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
