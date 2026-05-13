---
repo_name: ComposioHQ/agent-orchestrator
url: "https://github.com/ComposioHQ/agent-orchestrator"
stars: 6443
forks: 877
contributors_count: 29
last_commit_date: "2026-04-22T19:41:31+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-05-05T08:13:03.996044+00:00"
model: auto
duration_s: 350.3
clone_size_kb: 18163
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`ComposioHQ/agent-orchestrator` is a TypeScript monorepo that runs and supervises many coding-agent sessions in parallel, each isolated in its own branch/worktree and tracked as a lifecycle-driven session (`packages/core/src/session-manager.ts:1202-1467`, `packages/core/src/lifecycle-manager.ts:2422-2560`). A user typically runs `ao start` (or `ao start <repo-url>`), which starts a dashboard plus orchestrator process that spawns worker agents, routes CI/review feedback back to them, and escalates only when automation fails (`packages/cli/src/commands/start.ts:1-10`, `README.md:95-126`). The system is plugin-based: agent runtime, SCM, tracker, notifier, and terminal integrations are swappable (`packages/core/src/plugin-registry.ts:37-69`). In practice, this solves coordination overhead for “many-agent coding ops” rather than just launching one assistant.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen as a runtime framework in core orchestration. The orchestration layer is **custom**, built around plugin interfaces and a polling lifecycle engine (`packages/core/src/types.ts:453-556`, `packages/core/src/lifecycle-manager.ts:1-8`). There are references to “crewai” etc. in lock/docs artifacts, but not as the core control-plane import path for session orchestration.

Architecture-wise, the “intelligence” is split across:
- **Agent plugins** (Claude Code, Codex, Aider, Cursor, OpenCode, etc.) that define launch commands, activity-state extraction, restore behavior, and optional workspace hooks (`packages/core/src/types.ts:461-556`, `packages/plugins/agent-claude-code/src/index.ts:682-885`).
- **Session manager** that creates workspace -> launches runtime -> records metadata -> optionally delivers task prompt post-launch (`packages/core/src/session-manager.ts:1202-1431`).
- **Lifecycle manager** that periodically polls all sessions, detects state transitions, executes reactions (send-to-agent/notify/merge), and emits/escalates events (`packages/core/src/lifecycle-manager.ts:2422-2560`, `packages/core/src/lifecycle-manager.ts:1254-1377`).

So this is a multi-agent orchestration platform where each worker session is a concrete external coding agent process, coordinated by a custom manager.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker with event-driven reactions**.

- **Manager-worker:** central orchestrator/session manager spawns and supervises worker agents in isolated workspaces.
- **Event-driven overlay:** lifecycle poll cycles detect transitions and trigger configured reactions.

Control flow example (spawn path):

```1202:1210:packages/core/src/session-manager.ts
// Create workspace (if workspace plugin is available)
let workspacePath = project.path;
if (plugins.workspace) {
  const wsInfo = await plugins.workspace.create({
    projectId: spawnConfig.projectId,
    project,
    sessionId,
    branch,
```

```1287:1296:packages/core/src/session-manager.ts
const launchCommand = plugins.agent.getLaunchCommand(agentLaunchConfig);
const environment = plugins.agent.getEnvironment(agentLaunchConfig);

const handle = await plugins.runtime.create({
  sessionId: tmuxName ?? sessionId,
  workspacePath,
  launchCommand,
```

Control flow example (poll + reaction loop):

```2422:2451:packages/core/src/lifecycle-manager.ts
async function pollAll(): Promise<void> {
  ...
  const sessions = await sessionManager.list(scopedProjectId);
  ...
  await populatePREnrichmentCache(sessionsToCheck);

  // Poll all sessions concurrently
  await Promise.allSettled(sessionsToCheck.map((s) => checkSession(s)));
```

```2556:2560:packages/core/src/lifecycle-manager.ts
start(intervalMs = 30_000): void {
  if (pollTimer) return; // Already running
  pollTimer = setInterval(() => void pollAll(), intervalMs);
  void pollAll();
}
```

## 4. Tools & External Integrations

- **Terminal/runtime control (tmux/process):** worker agent processes run in runtime plugins; tmux runtime creates sessions, sends keys/messages, captures output (`packages/plugins/runtime-tmux/src/index.ts:52-167`).
- **GitHub SCM + CI/review APIs (via `gh` CLI):** PR detection, CI checks, review threads, merge readiness (`packages/plugins/scm-github/src/index.ts:1-5`, `packages/plugins/scm-github/src/index.ts:170-220`).
- **Trackers:** GitHub/Linear/GitLab tracker plugins (issue fetch + prompt context), wired through plugin registry (`packages/core/src/plugin-registry.ts:53-56`).
- **Workspace isolation:** worktree/clone plugins create per-session isolated repos (`packages/core/src/plugin-registry.ts:50-51`; spawn usage at `packages/core/src/session-manager.ts:1202-1223`).
- **Notifiers:** desktop, Slack, Discord, webhook, Composio, OpenClaw dispatch for escalation/alerts (`packages/core/src/plugin-registry.ts:60-65`, `packages/core/src/lifecycle-manager.ts:1953-1960`).
- **Terminal attachment surfaces:** iTerm2 + web terminal plugins (`packages/core/src/plugin-registry.ts:67-68`).
- **Agent-native stores/logs:** e.g., Claude/Codex JSONL session logs for activity and session info (`packages/plugins/agent-claude-code/src/index.ts:749-810`, `packages/plugins/agent-codex/src/index.ts:54-140`).

No vector DB/RAG pipeline is central here; the repo is orchestration + process/tool integration.

## 5. Notable Code Walkthrough

- `packages/core/src/types.ts:453-556` — Defines the `Agent` plugin contract (`getLaunchCommand`, `getActivityState`, restore/hooks methods). This is the core abstraction enabling heterogeneous LLM agents under one orchestrator.
- `packages/core/src/session-manager.ts:1202-1467` — Main worker-session spawn pipeline: create workspace, build prompt, launch runtime, persist metadata, and optionally post-launch prompt delivery.
- `packages/core/src/lifecycle-manager.ts:1254-1377` — Reaction execution engine (notify/send-to-agent/merge + retry/escalation logic), which operationalizes autonomy.
- `packages/plugins/agent-claude-code/src/index.ts:682-810` — Real adapter to an external coding agent CLI: launch command, env wiring, and activity-state detection from native JSONL.
- `packages/plugins/scm-github/src/index.ts:1-220` — GitHub integration layer using `gh` for PR/CI/review observability, feeding lifecycle transitions and reactions.

## 6. Use-Case Mapping

This repo partially fits **Browser / Terminal Use** because agent work is executed in terminal runtimes (tmux/process) and can be attached via terminal plugins (`packages/plugins/runtime-tmux/src/index.ts:56-93`, `packages/core/src/plugin-registry.ts:67-68`). But the dominant value is not terminal interaction itself; it is **automated workflow orchestration** across issue -> branch/worktree -> PR -> CI -> review -> merge lifecycle (`README.md:119-124`, `packages/core/src/lifecycle-manager.ts:1-8`, `packages/core/src/lifecycle-manager.ts:2422-2560`).

So the assigned label is somewhat narrow; better final category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong pluggable architecture across 7+ slots with explicit contracts (`packages/core/src/types.ts`, `packages/core/src/plugin-registry.ts`).
  - Practical multi-agent concurrency via isolated worktrees/sessions, not just prompt-level role-play (`packages/core/src/session-manager.ts:1202-1219`).
  - Mature lifecycle/reaction loop with retries, escalation, and event semantics (`packages/core/src/lifecycle-manager.ts:1254-1377`).
  - Supports heterogeneous real agents (Claude, Codex, Aider, etc.) behind one orchestrator API (`packages/core/src/plugin-registry.ts:43-48`).
  - Integrates directly with CI/review systems to close feedback loops automatically (`packages/plugins/scm-github/src/index.ts`).

- **Limitations:**
  - Polling-based lifecycle loop (`setInterval`) may add latency and operational overhead at larger scales (`packages/core/src/lifecycle-manager.ts:2556-2560`).
  - Heavy dependence on external CLIs and local environment correctness (`gh`, `tmux`, agent binaries), increasing fragility (`README.md:48`, `packages/plugins/runtime-tmux/src/index.ts:194-205`).
  - “Intelligence” is mostly procedural/rule-driven; limited explicit planner/graph reasoning compared with agent research frameworks.
  - Significant complexity in metadata/state reconciliation paths, which could be hard to verify formally (`packages/core/src/session-manager.ts`, `packages/core/src/lifecycle-manager.ts`).

- **Research relevance:**
  - Evidence of **production-style multi-agent software engineering orchestration** (manager controlling many autonomous coding workers).
  - Useful case study for **hybrid autonomy**: automated reactions with human escalation fallback.
  - Demonstrates **adapter-based interoperability** across multiple LLM agent backends under one lifecycle model.
  - Provides an example of **stateful, tool-grounded MAS** in real CI/review ecosystems rather than synthetic benchmarks.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
