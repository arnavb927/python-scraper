---
repo_name: cluesmith/codev
url: "https://github.com/cluesmith/codev"
stars: 256
forks: 35
contributors_count: 4
last_commit_date: "2026-04-23T02:56:53+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:33:49.828759+00:00"
model: auto
duration_s: 71.3
clone_size_kb: 30735
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`cluesmith/codev` is a TypeScript monorepo that provides a CLI-driven “agent farm” for software delivery workflows: users run commands like `afx spawn`, `porch next`, and `consult` to create builder agents, assign protocolized work, and run multi-model reviews. The system manages Git worktrees, persistent terminal sessions, and phase-gated protocol state to coordinate architect↔builder collaboration. In practice, a user gets an operational workflow engine that scaffolds, routes, verifies, and tracks multi-step development tasks (spec/plan/implement/review) rather than a single chat assistant. The dashboard/Tower server adds live monitoring and message routing across active agents.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen as a core runtime framework; it is a **custom orchestration system**. The runtime coordination is implemented in Codev’s own modules: `afx` for spawning/terminal orchestration (`packages/codev/src/agent-farm/commands/spawn.ts:17-846`), `porch` for protocol state machine planning (`packages/codev/src/commands/porch/next.ts:1-809`), and `consult` for external model review execution (`packages/codev/src/commands/consult/index.ts:1-1474`).

LLM “intelligence” is distributed across protocol templates and role prompts (e.g., protocol JSON + prompt markdown), while control logic lives in deterministic orchestration code. `porch` computes tasks from `status.yaml` + filesystem truth, emits next actions, and enforces gates/checks (`packages/codev/src/commands/porch/index.ts:122-461`, `packages/codev/src/commands/porch/protocol.ts:22-414`). `consult` connects to multiple model backends (Claude Agent SDK, OpenAI Codex SDK, Gemini/Hermes CLIs) and persists verdict artifacts consumed by `porch` for iterative review (`packages/codev/src/commands/consult/index.ts:366-764`, `packages/codev/src/commands/porch/next.ts:514-614`).

Architecturally, this is a multi-agent workflow system with explicit agent roles (architect, builder, shell), worktree isolation, message bus semantics via Tower, and phase-based progression (SPIR/ASPIR/BUGFIX/etc.) rather than autonomous free-form collaboration.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker** with a **state-machine planner**.

- **Manager/Planner:** `porch next` computes prescriptive tasks per phase/iteration (`packages/codev/src/commands/porch/next.ts:220-396`).
- **Workers:** spawned builders execute tasks in dedicated worktrees/terminals (`packages/codev/src/agent-farm/commands/spawn.ts:265-445`, `packages/codev/src/agent-farm/commands/spawn-worktree.ts:614-689`).
- **Feedback loop:** reviewers (`consult`) write verdict files; `porch` reads them and advances or requests rebuttals (`packages/codev/src/commands/porch/next.ts:514-649`).

Excerpt 1 (planner loop intent):
```9:16:packages/codev/src/commands/porch/next.ts
 * The builder loop:
 *   porch next → execute tasks → porch done → porch next → ...
 */
...
import { readState, writeStateAndCommit, findStatusPath, getProjectDir, resolveArtifactBaseName } from './state.js';
```

Excerpt 2 (runtime dispatch by builder type):
```837:845:packages/codev/src/agent-farm/commands/spawn.ts
const handlers: Record<BuilderType, () => Promise<void>> = {
  spec: () => spawnSpec(options, config),
  bugfix: () => spawnBugfix(options, config),
  task: () => spawnTask(options, config),
  protocol: () => spawnProtocol(options, config),
  shell: () => spawnShell(options, config),
  worktree: () => spawnWorktree(options, config),
};
```

## 4. Tools & External Integrations

- **LLM model backends:** Claude Agent SDK + OpenAI Codex SDK + Gemini/Hermes CLI adapters in `consult` (`packages/codev/src/commands/consult/index.ts:15-43`, `370-566`, `571-764`).
- **GitHub/forge APIs:** abstract “forge concept” command layer (default `gh` scripts, provider overrides) in `packages/codev/src/lib/forge.ts:1-413`; used for issues/PRs/comments and merge checks (`packages/codev/src/agent-farm/commands/spawn.ts:26-56`, `655-734`; `packages/codev/src/commands/consult/index.ts:777-929`).
- **Terminal/PTY automation:** persistent PTY sessions, shellper socket-backed terminals, websocket terminal streaming (`packages/codev/src/terminal/pty-manager.ts:41-437`; `packages/codev/src/agent-farm/servers/tower-server.ts:324-419`).
- **HTTP/WebSocket/SSE control plane (Tower):** API routes for spawning, sending messages, workspace status, dashboard events (`packages/codev/src/agent-farm/servers/tower-routes.ts:140-246`, `814-944`).
- **Git worktree automation:** per-agent branch/worktree lifecycle and porch initialization (`packages/codev/src/agent-farm/commands/spawn-worktree.ts:79-327`, `333-351`).
- **Local DB persistence:** Tower cron/task/session data via SQLite layer (`packages/codev/src/agent-farm/servers/tower-routes.ts:61-62`, `2203-2353`).
- **No MCP server dependency** was found as core runtime requirement in these orchestration paths.

## 5. Notable Code Walkthrough

- `packages/codev/src/commands/porch/next.ts:220-809` - Core planner/state machine: reads protocol + project state, emits next tasks, triggers consultation tasks, and handles review verdict iteration logic.
- `packages/codev/src/agent-farm/commands/spawn.ts:265-846` - Main agent launcher: validates modes, creates/recovers worktrees, builds initial prompts, starts builder/shell sessions, and registers active agents.
- `packages/codev/src/commands/consult/index.ts:1324-1474` - Consultation entrypoint: validates mode, resolves builder vs architect context, composes review prompts, dispatches to model backends, and writes outputs for `porch`.
- `packages/codev/src/agent-farm/servers/tower-routes.ts:814-944` - Cross-agent messaging endpoint (`/api/send`) implementing address resolution, formatting, and typing-aware deferred delivery.
- `codev/protocols/spir/protocol.json:12-172` - Protocol definition consumed by runtime planner: phase graph, build/verify semantics, model sets, checks, gates, and transitions.

## 6. Use-Case Mapping

This repository strongly realizes **Browser / Terminal Use** at runtime through persistent terminal orchestration, websocket/SSE streaming, and dashboard-centric agent operation (`tower-server.ts`, `tower-routes.ts`, `pty-manager.ts`). However, the *higher-level purpose* is broader: it automates software-development workflows (spec→plan→implement→review) across multiple agents and model reviewers. So while Browser/Terminal is a key interface mechanism, the better categorical fit for system intent is **Workflow Automation** (with terminal/browser as execution substrate).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Explicit, inspectable protocol state machine with enforceable gates/checks (`porch`).
  - Real multi-agent coordination across architect/builders/reviewers with durable artifacts.
  - Strong operational tooling: worktree isolation, terminal persistence, messaging bus, dashboard.
  - Multi-model review integration with iterative rebuttal loop (not just one-shot eval).
  - Forge abstraction allows non-GitHub provider customization.

- **Limitations:**
  - Heavy coupling to CLI/tooling environment (git, forge scripts, model CLIs/SDK auth).
  - Large orchestration surface increases operational complexity and failure modes.
  - Some checks and scripts are shell-command centric; portability and reproducibility vary.
  - Protocol correctness depends on template quality and disciplined human gate approvals.
  - Security model relies on local trust assumptions; many operations execute shell commands.

- **Research relevance:**
  - Evidence of practical hierarchical MAS for software engineering with explicit manager-worker loops.
  - Example of hybrid symbolic control (state machine) + LLM judgment (multi-model consultations).
  - Useful case for studying artifact-mediated coordination (files/verdicts/state) over direct agent-to-agent reasoning.
  - Demonstrates production-oriented agent ops patterns: persistence, observability, and controlled autonomy.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
