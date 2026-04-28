---
repo_name: unohee/OpenSwarm
url: "https://github.com/unohee/OpenSwarm"
stars: 587
forks: 102
contributors_count: 3
last_commit_date: "2026-04-20T13:20:49+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T15:33:21.317664+00:00"
model: auto
duration_s: 68.6
clone_size_kb: 3388
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

OpenSwarm is a TypeScript daemon/CLI (`openswarm`) that runs an autonomous software-delivery loop over Linear issues, executes code changes with LLM-driven worker/reviewer agents, and reports status through Discord and a web dashboard. In practice, users start the service and configure projects/integrations; the system then heartbeats, selects ready tasks, runs a multi-stage pipeline (worker/reviewer/tester/documenter), and updates Linear/GitHub state automatically. It can optionally isolate each task in a git worktree and auto-open PRs. The repo is not just a chatbot wrapper: it implements end-to-end operational automation around software tasks (selection, execution, QA, reporting, retry/backoff, and decomposition). The output a user gets is a continuously operating “AI dev team” workflow tied to issue trackers and CI.

## 2. Agent Framework & Architecture

This is a **custom agent framework**, not LangGraph/LangChain/CrewAI/AutoGen. I found no imports of those frameworks, and orchestration is implemented in local classes/modules (`src/agents/pairPipeline.ts`, `src/automation/autonomousRunner.ts`, `src/orchestration/decisionEngine.ts`). Model execution is done through CLI adapter abstractions for Claude/Codex/GPT/local (`src/adapters/index.ts:30-72`) rather than external orchestration SDKs.

The architecture has two layers. First is a **system-level orchestrator**: `AutonomousRunner` heartbeat fetches tasks, applies policy gates (time window, quota, pace, retries), and schedules execution (`src/automation/autonomousRunner.ts:579-699`, `:700-868`). Second is a **task-level multi-agent pipeline**: `PairPipeline` coordinates role agents (`worker`, `reviewer`, optional `tester`, `documenter`, `auditor`, `skill-documenter`) with iterative revise loops and stopping rules (`src/agents/pairPipeline.ts:165-214`, `:741-1009`).

“Intelligence” is distributed across (a) prompt builders in locale templates (`worker/reviewer/planner` prompt construction), (b) decision heuristics/policy logic in `DecisionEngine`, and (c) runtime feedback loops (confidence HALT, stuck detection, guard checks, reviewer revision cycles). A dedicated planner agent can decompose large issues into sub-issues before execution (`src/support/planner.ts:73-103`, `src/automation/runnerExecution.ts:232-514`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker** (with event-driven heartbeat triggers and iterative control loops).

- **Manager layer:** `AutonomousRunner` acts as supervisor that picks tasks and dispatches execution.
- **Worker team layer:** `PairPipeline` runs role agents in sequence and loops revisions until success/reject/max-iterations.

Control flow excerpts:

From heartbeat to execution dispatch:
`src/automation/autonomousRunner.ts:671-680`
```ts
const decision = await this.engine.heartbeat(filteredTasks);
...
if (decision.action === 'execute' && decision.task) {
  await this.executeTaskPairMode(decision.task);
} else if (decision.action === 'defer' && decision.task) {
  this.state.pendingApproval = decision.task;
  await this.requestApproval(decision);
}
```

Inside the task loop (`worker -> reviewer -> tester`, with revise/retry):
`src/agents/pairPipeline.ts:756-766`
```ts
while (context.currentIteration < maxIterations) {
  context.currentIteration++;
  const stuckCheck = this.stuckDetector.check();
  if (stuckCheck.isStuck) { ... return { success: false }; }
  ...
}
```

`src/agents/pairPipeline.ts:934-952`
```ts
if (decision === 'reject') {
  agentPair.updateSessionStatus(context.session.id, 'rejected');
  return { success: false };
}
if (decision === 'revise') {
  agentPair.trackFailure(context.session.id);
  ...
  continue;
}
```

## 4. Tools & External Integrations

- **LLM CLIs / model providers** (Claude, Codex, GPT, local): adapter registry and provider-specific parsing in `src/adapters/index.ts`, `src/adapters/claude.ts`.
- **Linear API** (`@linear/sdk`) for issue fetch/state/comments/sub-issues: `src/linear/linear.ts`.
- **Discord bot** (`discord.js`) for command/control and reporting: `src/discord/discordCore.ts`.
- **GitHub integration via `gh` CLI** for CI/PR checks/comments/logs: `src/github/github.ts`.
- **Git + Git worktrees + automated PR creation**: `src/support/worktreeManager.ts` and execution wiring in `src/automation/runnerExecution.ts:582-763`.
- **Web dashboard + SSE + GraphQL issue board APIs**: `src/support/web.ts`.
- **Knowledge graph / code impact analysis** used for planning and conflict detection: `src/knowledge/*`, called in pipeline/runner (`src/agents/pairPipeline.ts:222-230`, `:357-417`; `src/automation/autonomousRunner.ts:810-841`).
- **Persistent cognitive memory (local vector DB)** using LanceDB + local embeddings (`@xenova/transformers`): `src/memory/memoryCore.ts`.
- **Scheduler/cron automation** (`croner`) for heartbeat and maintenance: `src/automation/autonomousRunner.ts`, `src/core/service.ts`.

## 5. Notable Code Walkthrough

- `src/automation/autonomousRunner.ts:62-168,579-699,700-868` - Main runtime supervisor: heartbeat lifecycle, gating, task filtering, parallel scheduling, conflict-aware enqueue, and dispatch into pipeline execution.
- `src/agents/pairPipeline.ts:165-324,433-677,741-1009` - Core multi-agent execution engine: stage execution, confidence/stuck handling, reviewer-driven revision loop, tester/documenter optional stages, and final status construction.
- `src/automation/runnerExecution.ts:518-756` - Bridges orchestration to concrete task runs, including draft analysis injection, decomposition fallback, worktree isolation, pipeline event reporting, and PR creation.
- `src/orchestration/decisionEngine.ts:184-261,269-368,447-564` - Task decision/policy module: cooldown/consecutive limits, scope validation, prioritization, workflow mapping, and optional issue parsing/impact enrichment.
- `src/adapters/claude.ts:25-109` - Provider adapter implementation showing how LLM calls are actually made (`claude -p ... --output-format stream-json`) and parsed into structured worker/reviewer outputs.

## 6. Use-Case Mapping

The assigned label **Code Generation** is partially true at the agent role level (worker modifies repo files and reviewer validates), but the dominant system behavior is broader **Workflow Automation**: selecting tracked work from Linear, enforcing operational policies, orchestrating multi-agent execution, updating issue/CI/PR states, and reporting to Discord/dashboard. The repository is best categorized as **Workflow Automation** with embedded code-generation agents, rather than a pure code-generation framework or coding assistant SDK.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - End-to-end autonomous loop from issue intake to completion/PR, not just prompt wrappers.
  - Clear multi-agent separation (worker/reviewer/tester/documenter/auditor) with iterative control logic.
  - Strong operational safeguards: retries, confidence HALT, stuck detection, pace/quota/time-window gates.
  - Practical integration depth with Linear, GitHub, Discord, and web observability.
  - Worktree-based isolation per task reduces branch interference in concurrent runs.

- **Limitations:**
  - Heavy dependence on external CLIs (`claude`, `gh`, git environment); portability/reproducibility may vary.
  - Prompt/output parsing relies on structured text/JSON conventions that can fail with model drift.
  - Some hardcoded ops assumptions (paths, service behaviors) indicate environment coupling.
  - Complex policy surface (many gates/states) may be difficult to formally verify or tune.
  - No formal graph-orchestration DSL; behavior is spread across many modules, increasing maintenance load.

- **Research relevance:**
  - Useful evidence for **manager-worker MAS patterns** in real software operations.
  - Demonstrates hybrid orchestration combining symbolic policy gates with LLM role agents.
  - Shows practical confidence/stuck intervention mechanisms in iterative agent pipelines.
  - Good case study of integrating agentic coding with external socio-technical systems (issue tracker, CI, chat ops).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
