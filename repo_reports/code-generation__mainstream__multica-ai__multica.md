---
repo_name: multica-ai/multica
url: "https://github.com/multica-ai/multica"
stars: 19648
forks: 2392
contributors_count: 64
last_commit_date: "2026-04-23T05:36:55+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, Browser / Terminal Use]
generated_at: "2026-05-05T07:48:18.083002+00:00"
model: auto
duration_s: 113.4
clone_size_kb: 33828
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`multica-ai/multica` is a managed agent operations platform: users define agents, connect local runtimes (daemon), and assign those agents to workspace work items (issues, comments, chat sessions, autopilot triggers). In practice, a daemon process polls/claims queued tasks, prepares isolated git workspaces, invokes an underlying coding-agent CLI (Claude, Codex, Cursor, etc.), and streams outputs/events back to the server/UI. The user gets a team-style workflow where multiple AI agents can be assigned, mentioned, and scheduled, with task status, transcripts, retries, and issue/chat integration. It is not just a prompt wrapper; it is an orchestration/control plane for agent execution across workspaces and repos.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex. A direct scan shows no such imports, and orchestration is implemented in custom Go services/daemon code (`server/internal/daemon`, `server/internal/service`, `server/pkg/agent`). The core abstraction is a provider-agnostic backend interface (`server/pkg/agent/agent.go:15-44`) with concrete adapters for many CLIs (`claude`, `codex`, `cursor`, `copilot`, etc.; `server/pkg/agent/agent.go:97-129`).

Architecture is split into: (1) server-side task queue + lifecycle APIs, (2) local daemon runtime that registers runtimes and claims tasks, and (3) provider backends that translate a generic execution contract into each CLI protocol (`stream-json` or Codex JSON-RPC app-server). Task intelligence is mostly encoded in prompt/context assembly (`server/internal/daemon/prompt.go`, `server/internal/daemon/execenv/runtime_config.go`), agent-specific instructions/skills from DB, and event-driven lifecycle management (enqueue, claim, start, complete/fail, retry).

The system supports many agents in parallel at platform level (different assignees/runtimes/tasks), but each claimed task executes through a single selected agent backend. Notably, native Codex sub-agent fanout is explicitly disabled by default in daemon-managed sessions due to lifecycle consistency concerns (`server/internal/daemon/execenv/codex_multi_agent.go:13-31`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker + event-driven queue orchestration**.

- **Manager/dispatcher layer:** `TaskService` enqueues and claims tasks per runtime/agent concurrency limits (`server/internal/service/task.go:393-549`).
- **Worker layer:** daemon poll loop claims and executes tasks via provider backend (`server/internal/daemon/daemon.go:1063-1151`, `1287-1658`).
- **Event-driven glue:** enqueue/claim/completion emits bus events and wakeups (`server/internal/service/task.go:1225-1248`, `1250-1303`).

Control-flow excerpts:

From poll/claim to worker spawn (`server/internal/daemon/daemon.go:1093-1127`):
```go
task, err := d.client.ClaimTask(ctx, rid)
...
if task != nil {
    wg.Add(1)
    d.activeTasks.Add(1)
    go func(t Task, slot int) {
        defer wg.Done()
        defer d.activeTasks.Add(-1)
        defer func() { sem <- slot }()
        d.handleTask(ctx, t, slot)
    }(*task, slot)
}
```

From runtime-level candidate selection to per-agent claim (`server/internal/service/task.go:506-538`):
```go
tasks, err := s.Queries.ListQueuedClaimCandidatesByRuntime(ctx, runtimeID)
...
for _, candidate := range tasks {
    task, err := s.ClaimTask(ctx, candidate.AgentID)
    ...
    if task != nil && task.RuntimeID == runtimeID {
        claimed = task
        break
    }
}
```

## 4. Tools & External Integrations

- **Agent CLIs (core execution backends):** Claude/Codex/Cursor/Copilot/OpenCode/OpenClaw/Hermes/Gemini/Pi/Kimi/Kiro wired via unified backend factory (`server/pkg/agent/agent.go:97-129`), with per-provider process/protocol adapters (`server/pkg/agent/claude.go`, `server/pkg/agent/codex.go`).
- **MCP server configs:** per-agent `mcp_config` is passed to backends (e.g., Claude writes temp MCP config and adds `--mcp-config`; `server/pkg/agent/claude.go:40-54`, `558-575`; also propagated in daemon exec opts `server/internal/daemon/daemon.go:1477-1507`).
- **Git + worktrees:** daemon repo cache does `git clone --bare`, `git fetch`, and `git worktree add` for task workdirs (`server/internal/daemon/repocache/cache.go:92-137`, `370-506`).
- **Multica CLI as tool API for agents:** runtime config injects explicit command catalog (`multica issue ...`, `repo checkout`, `autopilot ...`) into `AGENTS.md`/`CLAUDE.md` (`server/internal/daemon/execenv/runtime_config.go:45-337`).
- **Server API + daemon transport:** daemon uses HTTP API endpoints for claim/start/progress/messages/complete/fail/heartbeat (`server/internal/daemon/client.go:109-258`), with WS/event bus on server side (`TaskService` broadcasts events; `server/internal/service/task.go:1250-1354`).
- **Database-backed queue/lifecycle:** task claim and state transitions are DB-query driven (`server/internal/service/task.go`, `server/pkg/db/generated/*.go`).

No vector DB/RAG stack (Chroma/Pinecone/pgvector retrieval pipeline for prompting) appears in execution path.

## 5. Notable Code Walkthrough

- `server/internal/daemon/daemon.go:1063-1853` — Core runtime loop: polling, capacity semaphore, claim/start/cancel monitoring, backend execution, stream draining, usage reporting, and terminal task updates. This is the operational heart of agent orchestration.
- `server/internal/service/task.go:393-549` — Server-side claim logic enforcing per-agent concurrency and runtime-level candidate selection; this determines fairness and dispatch behavior across many agents.
- `server/pkg/agent/codex.go:33-384` — Codex app-server adapter implementing JSON-RPC lifecycle (`initialize`, `thread/start|resume`, `turn/start`), parsing tool/text events, and producing normalized `Result`.
- `server/internal/daemon/execenv/runtime_config.go:45-337` — Generates runtime-specific instruction files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) and the concrete command/tool policy agents should follow.
- `server/internal/service/autopilot.go:34-231` — Automated trigger path that creates runs and either opens issues or dispatches direct run-only tasks, showing how “agent workflows” are scheduled/orchestrated.

## 6. Use-Case Mapping

The assigned label **Code Generation** is only partially correct. The codebase certainly executes coding agents against repos (checkout/worktree + coding CLIs), but the dominant implemented behavior is broader: queueing, scheduling, assignee routing, comments/chat/autopilot triggers, retries, and workspace event orchestration. In other words, it operationalizes agents as workers inside a structured team workflow rather than focusing purely on code synthesis. A better primary category is **Workflow Automation** (with strong code-generation capability as a major sub-use-case).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Provider-agnostic backend abstraction with many real agent CLIs under one execution contract (`server/pkg/agent/agent.go`).
  - Robust task lifecycle engineering: enqueue/claim/start/complete/fail, retries, cancellation polling, usage reporting, and event broadcasting.
  - Practical repo execution model (bare cache + per-task worktrees) for reproducible coding tasks.
  - Rich context injection pipeline (agent identity, skills, project resources, command policy) instead of thin one-shot prompts.
  - Explicit handling of failure/edge cases (orphan recovery, stale sessions, blocked outputs, runtime offline).

- **Limitations:**
  - Limited explicit inter-agent reasoning/planning protocols; coordination is mostly task handoff/events rather than planner-worker cognitive decomposition.
  - Codex native multi-agent mode is disabled by default due lifecycle risk, reducing nested-agent experimentation in production path (`codex_multi_agent.go`).
  - Heavy coupling to CLI behaviors/protocol quirks; backend maintenance burden rises as upstream CLIs evolve.
  - No explicit arbitration/debate/consensus mechanisms among peer agents.
  - Tooling depends on local daemon + environment setup, which adds operational complexity.

- **Research relevance:**
  - Strong evidence for **production multi-agent operations infrastructure** (dispatch, runtime control, lifecycle reliability) rather than toy orchestration demos.
  - Useful case study for **event-driven MAS in software engineering workflows** (issues/comments/chat/autopilot-triggered agent actions).
  - Demonstrates a **unified execution abstraction across heterogeneous agent runtimes**.
  - Illustrates real-world trade-offs between advanced multi-agent features and operational safety (e.g., disabling native subagent fanout).

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
