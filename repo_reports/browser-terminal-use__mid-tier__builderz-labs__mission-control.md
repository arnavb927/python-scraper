---
repo_name: builderz-labs/mission-control
url: "https://github.com/builderz-labs/mission-control"
stars: 4300
forks: 741
contributors_count: 34
last_commit_date: "2026-04-21T07:00:49+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 8
architecture_labels: [LangGraph, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T09:56:41.747299+00:00"
model: auto
duration_s: 106.8
clone_size_kb: 23946
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`mission-control` is a self-hosted Next.js control plane for running and supervising AI agents, with a dashboard plus REST APIs for tasks, sessions, and runtime health. In practice, a user runs the web app, defines agents/tasks, and the server scheduler continuously routes tasks, dispatches them to agent runtimes (primarily OpenClaw gateway or direct Claude API), and tracks outcomes in SQLite. It also provides operational controls like retries, stale-task recovery, quality review, audit logs, and token accounting. So the user gets an “AI ops center” rather than a single chatbot: queueing, assignment, execution, review, and monitoring in one place.

## 2. Agent Framework & Architecture

This repo does **not** directly implement LangGraph/AutoGen/CrewAI internals via their SDKs. The orchestration layer is mostly **custom TypeScript**, with external runtime calls via OpenClaw CLI/gateway and Anthropic API (`src/lib/task-dispatch.ts:221-294`, `src/lib/openclaw-gateway.ts:40-65`, `src/lib/command.ts:79-94`).  

It does include adapter classes named for frameworks (`langgraph`, `autogen`, `crewai`), but they are thin compatibility shims that broadcast status/events and query assignments, not native framework execution graphs (`src/lib/adapters/langgraph.ts:5-49`, `src/lib/adapters/index.ts:9-22`, `src/app/api/adapters/route.ts:18-116`).

Architecturally, “intelligence” is split across:
- prompt templates and task/review instructions (`buildTaskPrompt`, `buildReviewPrompt`) in `src/lib/task-dispatch.ts:74-100` and `321-357`;
- a scheduler loop that triggers routing, dispatch, review, and recovery every minute (`src/lib/scheduler.ts:365-460`);
- database-backed task state transitions (`inbox -> assigned -> in_progress -> review/quality_review -> done|failed`) in `src/lib/task-dispatch.ts:623-881`.

It is therefore a multi-agent workflow orchestrator with explicit control logic and state transitions, not a single-agent chat app.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker with event-driven scheduling**.

- Manager layer: scheduler plus routing/dispatch/review functions (`src/lib/scheduler.ts:418-469`, `src/lib/task-dispatch.ts:936-1033`, `623-881`, `371-539`).
- Worker layer: assigned runtime agents execute tasks; a special reviewer agent (“Aegis”) validates outputs and can reject/requeue.

Control flow excerpt (scheduler chaining route + dispatch + review scheduling):

```611:459:src/lib/scheduler.ts
: id === 'task_dispatch' ? await autoRouteInboxTasks().then(async (routeResult) => {
    const dispatchResult = await dispatchAssignedTasks()
    const parts = [routeResult.message, dispatchResult.message].filter(m => m && !m.includes('No '))
    return { ok: routeResult.ok && dispatchResult.ok, message: parts.join(' | ') || 'No tasks to route or dispatch' }
  })
: id === 'aegis_review' ? await runAegisReviews()
```

Control flow excerpt (worker completion then reviewer gate):

```776:483:src/lib/task-dispatch.ts
db.prepare(`
  UPDATE tasks SET status = ?, outcome = ?, resolution = ?, metadata = ?, updated_at = ? WHERE id = ?
`).run('review', 'success', truncated, JSON.stringify(existingMeta), Math.floor(Date.now() / 1000), task.id)

... // later in runAegisReviews
if (verdict.status === 'approved') {
  ...run('done', ...)
} else {
  ...run('assigned', `Aegis rejected: ${verdict.notes}`, ...)
}
```

## 4. Tools & External Integrations

- **OpenClaw gateway/CLI** (primary runtime transport for agent calls, session control, channel actions): `src/lib/openclaw-gateway.ts:40-65`, `src/lib/task-dispatch.ts:726-755`, `src/app/api/sessions/route.ts:65-159`, `src/app/api/spawn/route.ts:54-83`, `src/app/api/channels/route.ts:149-183`.
- **Anthropic Claude Messages API** (direct fallback when gateway unavailable; also used for script security review): `src/lib/task-dispatch.ts:221-294`, `src/lib/agent-runtimes.ts:106-160`.
- **SQLite (better-sqlite3)** for orchestration state, tasks, reviews, tokens, events: pervasive via `getDatabase`, especially `src/lib/task-dispatch.ts` and `src/lib/scheduler.ts`.
- **Event bus / SSE-style internal broadcasting** for task/agent lifecycle updates: `src/lib/event-bus.ts:42-70`.
- **Terminal/PTY integration** via `node-pty` + `tmux` for attaching to agent sessions: `src/lib/pty-manager.ts:53-113`, `src/app/api/pty/setup/route.ts:10-45`.
- **Local runtime/session scanners** for Claude/Codex/Hermes/OpenCode session visibility: `src/app/api/sessions/route.ts:23-40`, `200-352`; runtime detection/install in `src/lib/agent-runtimes.ts`.
- **Channel/web integrations through gateway RPC** (e.g., WhatsApp login flows): `src/app/api/channels/route.ts:306-383`.
- **Memory search (RAG-like retrieval utility)** with SQLite FTS5 over markdown/text memory files: `src/lib/memory-search.ts:22-37`, `168-239`.

## 5. Notable Code Walkthrough

- `src/lib/task-dispatch.ts:623-1033` - Core orchestration engine: dispatches assigned tasks to agents, records outcomes, handles retries/failures, and auto-routes inbox tasks to best-fit agents using heuristic scoring/capacity checks.
- `src/lib/task-dispatch.ts:371-539` - Implements the “Aegis” reviewer agent loop: reviews completed work, approves to `done` or rejects back to `assigned`, with capped rejection retries and escalation comments.
- `src/lib/scheduler.ts:365-460` - Global minute-tick orchestration loop; wires together auto-routing, dispatch, quality review, stale-task requeue, and other maintenance jobs.
- `src/app/api/adapters/route.ts:18-116` - Framework-agnostic adapter endpoint (`register/heartbeat/report/assignments/disconnect`) enabling external agent frameworks to integrate with Mission Control.
- `src/app/api/spawn/route.ts:54-117` - Ad hoc agent spawning endpoint using OpenClaw `sessions_spawn`, including model/tool profile selection and compatibility fallback behavior.

## 6. Use-Case Mapping

Assigned label `Browser / Terminal Use` is **partially** true but not primary. The repo does expose terminal/session operations (PTY+tmux attachment, local CLI session scanning, session controls) (`src/lib/pty-manager.ts:4-6`, `src/app/api/sessions/route.ts:23-40`). However, the dominant behavior in code is **workflow orchestration**: task queueing, routing, dispatch, review, retries, and governance loops (`src/lib/scheduler.ts:418-469`, `src/lib/task-dispatch.ts:623-1033`).  

So the better top-level category is **Workflow Automation**, with terminal/browser capabilities as operational interfaces.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Clear end-to-end multi-agent lifecycle with explicit task states and retry/escalation semantics (`src/lib/task-dispatch.ts`).
- Built-in quality gate agent (“Aegis”) adds reviewer-worker separation rather than blind completion (`src/lib/task-dispatch.ts:371-539`).
- Runtime-agnostic integration surface through adapters and OpenClaw gateway abstraction (`src/app/api/adapters/route.ts`, `src/lib/openclaw-gateway.ts`).
- Strong ops orientation: scheduler, heartbeat checks, stale-task recovery, auditability (`src/lib/scheduler.ts`, `src/lib/event-bus.ts`).
- Practical security checks on prompt/installer ingestion (`src/app/api/spawn/route.ts:29-46`, `src/lib/agent-runtimes.ts:73-99`).

- **Limitations:**
- “Framework adapters” are mostly event wrappers; no deep native LangGraph/AutoGen/CrewAI graph semantics in-process (`src/lib/adapters/*.ts`).
- Routing/planning is mostly heuristic keyword scoring, not learned planning/policy optimization (`src/lib/task-dispatch.ts:887-930`).
- Heavy dependence on OpenClaw/runtime availability; fallback behavior exists but adds complexity and failure modes (`src/lib/task-dispatch.ts:698-755`).
- Reviewer loop is bounded and simplistic (binary approve/reject parsing), potentially brittle on nuanced outputs (`src/lib/task-dispatch.ts:359-365`).
- True inter-agent collaboration (peer-to-peer message passing among workers) is limited; coordination is largely centralized manager-mediated.

- **Research relevance:**
- Useful evidence of a production-style **manager-worker + reviewer** multi-agent control loop with persistent state.
- Demonstrates practical orchestration concerns (liveness, retries, stale work recovery, audit trails) often absent in toy MAS benchmarks.
- Illustrates framework-agnostic “agent control plane” design where orchestration is decoupled from underlying model/runtime.
- Shows how enterprise governance features (role auth, rate limits, security scanning) integrate with MAS operations.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
