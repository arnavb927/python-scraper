---
repo_name: paperclipai/paperclip
url: "https://github.com/paperclipai/paperclip"
stars: 57840
forks: 9939
contributors_count: 98
last_commit_date: "2026-04-23T03:07:41+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T10:12:37.814858+00:00"
model: auto
duration_s: 130.1
clone_size_kb: 35641
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`paperclipai/paperclip` is an orchestration control plane for running many coding agents as a company-like workflow, not a single chat assistant. A user runs the server/UI, creates companies/agents, assigns issues, and Paperclip continuously schedules “heartbeat runs” that wake agents, execute adapter-specific LLM CLIs (Claude/Codex/Cursor/Gemini/etc.), and persist run state. The system handles issue checkout/locking, dependency-aware queueing, retries, environment leasing (local/SSH/sandbox/plugin), and runtime service management so work can proceed with minimal human intervention. The concrete output is tracked issue progress, comments/logs, run artifacts, and automated handoffs/recovery across many concurrent agent runs.

## 2. Agent Framework & Architecture

This repo uses a **custom orchestration framework** (TypeScript services + DB state machines), not LangGraph/LangChain/AutoGen/CrewAI at runtime. I found no runtime imports of those frameworks in source; the actual execution path is custom (`server/src/services/heartbeat.ts`, `server/src/adapters/registry.ts`, adapter `execute.ts` files). Adapters are registered as `ServerAdapterModule`s and invoked via `adapter.execute(...)`, with each adapter wrapping a concrete tool runtime (CLI process, HTTP gateway, or plugin adapter).

High-level architecture:
- **Control-plane orchestrator:** `heartbeatService` drives queued/running runs, claim logic, retries, session state, budget/hold checks, and lifecycle recovery (`server/src/services/heartbeat.ts:1978+`).
- **Task/ownership layer:** issue checkout/release enforces single-assignee and run ownership semantics (`server/src/services/issues.ts:2880+`).
- **Execution substrate:** environment drivers and orchestrator acquire/release leases and resolve execution targets (`server/src/services/environment-runtime.ts:166+`, `server/src/services/environment-run-orchestrator.ts:121+`).
- **Adapter layer:** concrete model/tool integrations (Claude/Codex/etc.) run processes, build prompts/env, parse outputs (`packages/adapters/*/src/server/execute.ts`).

The “intelligence” is distributed across:
1) adapter prompts/templates and wake payload shaping (`packages/adapters/claude-local/src/server/execute.ts:310+`, `packages/adapters/codex-local/src/server/execute.ts:282+`),  
2) orchestration policy/heuristics in heartbeat queueing/claiming/recovery (`server/src/services/heartbeat.ts:3733+, 4564+`),  
3) strict issue-state constraints (checkout locks and conflict logic) in issue service (`server/src/services/issues.ts:2880+`).

## 3. Orchestration Pattern

Closest match: **hierarchical + event-driven workflow orchestration** (manager-worker style), with DB-backed queue/state transitions rather than agent-to-agent direct messaging.

- “Manager”: heartbeat scheduler and run-claim logic (`startNextQueuedRunForAgent`, `claimQueuedRun`) decides which run can execute next.
- “Workers”: individual agent runs via adapter execution.
- Event-driven pieces: wakeup requests, deferred/coalesced wake handling, scheduled retries, and periodic recovery ticks.

Control-flow excerpt (queue → claim → execute):
```4564:4633:server/src/services/heartbeat.ts
async function startNextQueuedRunForAgent(agentId: string) {
  ...
  const queuedRuns = await db.select().from(heartbeatRuns)...
  const prioritizedRuns = [...queuedRuns].sort(...)
  for (const queuedRun of prioritizedRuns) {
    const claimed = await claimQueuedRun(queuedRun);
    if (claimed) claimedRuns.push(claimed);
  }
  for (const claimedRun of claimedRuns) {
    void executeRun(claimedRun.id)...
  }
}
```

Control-flow excerpt (actual adapter invocation):
```5458:5484:server/src/services/heartbeat.ts
const adapter = getServerAdapter(agent.adapterType);
const adapterResult = await adapter.execute({
  runId: run.id,
  agent,
  runtime: runtimeForAdapter,
  config: runtimeConfig,
  context,
  executionTarget,
  onLog,
  onMeta: onAdapterMeta,
});
```

## 4. Tools & External Integrations

- **LLM coding CLIs/adapters** (Claude, Codex, Cursor, Gemini, OpenCode, Pi, Hermes, plus process/http): wired in adapter registry and per-adapter execute modules (`server/src/adapters/registry.ts:120+`, `packages/adapters/*/src/server/execute.ts`).
- **Local shell/process execution** for agent runs and workspace/runtime jobs: `runAdapterExecutionTargetProcess`, `spawn`, shell commands (`packages/adapters/*/src/server/execute.ts`, `server/src/services/workspace-runtime.ts:2038+`).
- **Remote execution targets** (SSH/sandbox/plugin environments): lease + workspace realization + execution target resolution (`server/src/services/environment-runtime.ts:209+`, `server/src/services/environment-run-orchestrator.ts:230+`).
- **Plugin tool ecosystem (agent-callable tools)** with namespaced discovery/dispatch via worker RPC (`server/src/services/plugin-tool-registry.ts:227+`, `server/src/services/plugin-tool-dispatcher.ts:222+`).
- **Plugin worker processes** (JSON-RPC over stdio, isolation/restart/backoff): (`server/src/services/plugin-worker-manager.ts:1+`).
- **Database-backed orchestration state** (Drizzle/Postgres tables for runs/issues/leases/sessions) across heartbeat and issue services (`server/src/services/heartbeat.ts`, `server/src/services/issues.ts`).
- **Git/worktree automation** for task workspaces (`git worktree add/remove`, branch handling) (`server/src/services/workspace-runtime.ts:981+`).
- **Runtime service/dev server orchestration** (spawn service processes, readiness checks, reuse policies) (`server/src/services/workspace-runtime.ts:2320+`).

No vector-store/RAG pipeline appears central in the runtime path I inspected.

## 5. Notable Code Walkthrough

- `server/src/services/heartbeat.ts:1978-7518`  
  Core scheduler/orchestrator: queues, claims, executes runs, resolves session continuation, handles retries/recovery, and coordinates issue execution promotion/deferred wakes.

- `server/src/services/issues.ts:2880-3157`  
  Implements atomic issue checkout/release with run ownership and conflict semantics (`checkoutRunId`, `executionRunId`), which enforces single-agent task control.

- `server/src/services/environment-run-orchestrator.ts:121-506`  
  Central environment lifecycle orchestration for each run: resolve environment, acquire lease, realize workspace, resolve execution transport/target, and release with activity logging.

- `server/src/adapters/registry.ts:120-563`  
  Registers built-in and external adapters; defines adapter capabilities and maps adapter type to executable runtime implementation.

- `packages/adapters/claude-local/src/server/execute.ts:302-777` (similar in Codex adapter)  
  Concrete agent execution routine: builds prompts/context/env, manages session resume/fallback, runs CLI, parses outputs, emits usage/error/session metadata back to heartbeat.

## 6. Use-Case Mapping

Although agents perform code-generation tasks through coding CLIs, the repo’s dominant runtime behavior is **orchestrating multi-agent work pipelines**: assignment, queueing, dependency gating, lock management, retries, and recovery across many agents/issues. So the upstream “Code Generation” label is partially true at the leaf execution layer, but the primary system category is better described as **Workflow Automation** for agent companies. Code generation is an important capability of workers, while the main product differentiator is control-plane orchestration and operational governance.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong production-style orchestration invariants (issue checkout locks, run ownership, dependency gating).
  - Rich failure/recovery logic (orphan reaping, scheduled retries, deferred/coalesced wakes).
  - Pluggable execution stack: adapters + plugin tools + plugin environment drivers.
  - Environment abstraction supports local/SSH/sandbox/plugin with lease lifecycle.
  - Good observability surfaces (run events, activity logs, process metadata, runtime service tracking).

- **Limitations:**
  - High architectural complexity; core orchestration is concentrated in very large services (notably `heartbeat.ts`), increasing maintenance and verification burden.
  - Intelligence is mostly policy/rules + adapter prompts; limited explicit planning/debate between specialized cognitive agents.
  - Heavy dependence on external CLI tool behavior for model interaction quality and determinism.
  - Concurrency and state transitions rely on careful DB logic; subtle race conditions remain a risk in such designs.
  - Framework-agnostic custom stack means fewer reusable abstractions compared with graph-based agent frameworks.

- **Research relevance:**
  - Real-world evidence of **multi-agent workflow orchestration** as stateful control-plane engineering, not just prompt chaining.
  - Useful case study in **manager-worker scheduling with DB-backed consistency constraints**.
  - Illustrates practical patterns for **agent runtime isolation, plugin extensibility, and failure recovery**.
  - Demonstrates how “agentic AI” systems blend LLM execution with classical distributed systems concerns.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
