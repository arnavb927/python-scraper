---
repo_name: snarktank/antfarm
url: "https://github.com/snarktank/antfarm"
stars: 2421
forks: 438
contributors_count: 14
last_commit_date: "2026-02-26T17:39:04+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation]
generated_at: "2026-04-27T14:09:01.938046+00:00"
model: auto
duration_s: 80.7
clone_size_kb: 26614
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`antfarm` is a Node/TypeScript orchestration layer that installs predefined multi-agent workflows into OpenClaw, then runs them as automated pipelines. A user typically runs commands like `antfarm install` and `antfarm workflow run <workflow> "<task>"`, which creates a run in SQLite, provisions role-specific agents/workspaces, and starts cron-driven agent polling. Each agent claims work, executes instructions in its own session, and reports completion/failure back through `antfarm step complete` / `step fail`. The output is not a generated app directly by Antfarm itself, but a coordinated set of code changes, tests, PR actions, and workflow telemetry produced by multiple OpenClaw agents.

## 2. Agent Framework & Architecture

This is a **custom orchestration framework on top of OpenClaw**, not LangGraph/LangChain/CrewAI/AutoGen. Evidence: runtime code only depends on basic libs (`yaml`, `json5`) and Node APIs (`package.json:16-23`), while agent execution is delegated through OpenClaw cron/session tooling (`src/installer/agent-cron.ts:183-191`, `src/installer/gateway-api.ts:196-200`).

Architecture is declarative + DB-backed. Workflows define agents, roles, and ordered steps in YAML (`workflows/feature-dev/workflow.yml:16-390`). At run start, Antfarm parses the workflow spec, writes `runs` and `steps` rows, and sets first step pending (`src/installer/run.ts:26-47`). Agents are provisioned with isolated workspaces and role-based tool policies in OpenClaw config (`src/installer/agent-provision.ts:37-102`, `src/installer/install.ts:74-146`, `src/installer/install.ts:209-230`).

The “intelligence” mostly lives in prompt templates and role docs, not in a symbolic planner algorithm. Prompt templates are in workflow step `input` blocks (`workflows/feature-dev/workflow.yml:90-384`) and agent behavior constraints in per-agent files (`workflows/feature-dev/agents/planner/AGENTS.md:1-115`). Runtime logic handles scheduling/state transitions/retries/story loops (`src/installer/step-ops.ts:485-1103`) rather than generating plans itself.

## 3. Orchestration Pattern

Closest match: **hierarchical sequential pipeline with looped sub-stage (manager-worker style)**.

- Central controller (Antfarm runtime) enforces step order and shared context via DB state (`src/installer/step-ops.ts:494-507`, `src/installer/step-ops.ts:913-958`).
- Workers (OpenClaw agents) are independently scheduled by cron, claim work, execute, and report status (`src/installer/agent-cron.ts:134-157`, `src/cli/cli.ts:372-403`).
- One step can be looped over story items with optional verify-each feedback cycle (`src/installer/step-ops.ts:534-640`, `src/installer/step-ops.ts:730-845`).

Control flow excerpt 1 (`src/installer/step-ops.ts:494-507`):
```txt
WHERE s.agent_id = ? AND s.status = 'pending'
...
AND NOT EXISTS (
  SELECT 1 FROM steps prev
  WHERE prev.run_id = s.run_id
    AND prev.step_index < s.step_index
    AND prev.status NOT IN ('done', 'skipped')
)
ORDER BY s.step_index ASC
```

Control flow excerpt 2 (`src/installer/agent-cron.ts:140-151`):
```txt
Step 2 — If "HAS_WORK", claim the step:
node ... step claim "<agent>"
...
Then call sessions_spawn with these parameters:
- agentId: "<workflow_agent>"
- model: "<model>"
- task: ... full work prompt ... + CLAIMED STEP JSON
```

## 4. Tools & External Integrations

- **OpenClaw Gateway API (`/tools/invoke`)** for cron/session tool invocation; used to create/list/remove cron jobs and send session messages (`src/installer/gateway-api.ts:196-217`, `src/installer/gateway-api.ts:282-314`, `src/installer/gateway-api.ts:367-422`).
- **OpenClaw CLI fallback** (`openclaw cron ...`, `openclaw tool run ...`) when gateway is unavailable (`src/installer/gateway-api.ts:96-106`, `src/installer/gateway-api.ts:133-178`, `src/installer/gateway-api.ts:405-421`).
- **Shell/git/gh usage by agents** through workflow prompts (e.g., `gh pr create`, `gh pr view`, `git diff`, test/build commands) (`workflows/feature-dev/workflow.yml:317-353`, `workflows/bug-fix/workflow.yml:226-230`).
- **SQLite persistence** (`node:sqlite`) for runs/steps/stories state machine (`src/db.ts:1-4`, `src/db.ts:27-104`).
- **Filesystem workspaces and skill copying** for agent bootstrap files and skills (`src/installer/agent-provision.ts:56-76`, `src/installer/agent-provision.ts:129-173`).
- **Webhook notifications** per run via `notify_url` on emitted events (`src/installer/events.ts:29-46`, `src/installer/events.ts:64-80`).
- **No vector DB/RAG pipeline** found in runtime code.

## 5. Notable Code Walkthrough

- `src/installer/step-ops.ts:485-1103` - Core execution engine: claims steps, resolves template context, handles looped story execution, verify/retry semantics, pipeline advancement, and failure escalation.
- `src/installer/agent-cron.ts:128-250` - Cron orchestration layer: builds polling/work prompts, configures per-agent model selection, and maintains run-scoped cron lifecycle.
- `src/installer/install.ts:74-273` - Installation/config integration: maps agent roles to tool permissions, writes OpenClaw agent entries, and enforces guardrails (e.g., preserve main default agent).
- `workflows/feature-dev/workflow.yml:87-390` - Canonical multi-agent pipeline spec for feature delivery (planner/setup/developer/verifier/tester/reviewer) with explicit inter-step contracts and outputs.
- `src/installer/gateway-api.ts:120-422` - Integration adapter that bridges Antfarm runtime to OpenClaw tools through HTTP first and CLI fallback, making orchestration robust across environments.

## 6. Use-Case Mapping

The assigned primary use case (**Code Generation**) is partly true but incomplete. In `feature-dev`, developer/fixer agents do generate and modify code, tests, and PRs (`workflows/feature-dev/workflow.yml:147-199`, `workflows/bug-fix/workflow.yml:166-201`). However, the repository’s core product is broader **workflow orchestration**: provisioning agents, scheduling turns, tracking state, retries, escalation, and cross-role handoffs (`src/installer/run.ts:26-47`, `src/installer/step-ops.ts:913-958`). So the better top-level category is **Workflow Automation** with code generation as one workflow outcome.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, declarative workflow specs with explicit role separation and output contracts (`workflows/*/workflow.yml`).
  - Robust state machine handling for retries, abandoned work recovery, and loop verification (`src/installer/step-ops.ts:274-384`, `src/installer/step-ops.ts:779-907`).
  - Practical integration strategy (HTTP + CLI fallback) for reliability in heterogeneous OpenClaw setups (`src/installer/gateway-api.ts:120-179`, `259-273`).
  - Strong operational scaffolding: event log, dashboard daemon, medic watchdog, resumable runs (`src/installer/events.ts:86-117`, `src/cli/cli.ts:541-656`).
  - Runtime-enforced multi-agent coordination via shared DB context and step gating, not just prompt suggestions.

- **Limitations:**
  - Agent cognition quality is highly prompt-dependent; little algorithmic reasoning/planning beyond templated prompts (`workflows/feature-dev/workflow.yml:90-390`).
  - Tight coupling to OpenClaw-specific tools (`cron`, `sessions_spawn`, `sessions_send`) limits portability (`src/installer/agent-cron.ts:147-151`, `src/installer/gateway-api.ts:367-422`).
  - Shared context uses loosely typed `KEY: value` parsing, which can be brittle for complex structured outputs (`src/installer/step-ops.ts:24-54`, `694-703`).
  - Security/trust model assumes agents follow mandatory completion protocol; runtime compensates but cannot fully prevent misbehavior (`src/installer/agent-cron.ts:16-51`, `src/installer/step-ops.ts:274-350`).
  - No learned routing/adaptation; orchestration is predefined YAML plus deterministic status transitions.

- **Research relevance:**
  - Good evidence of **production-style hierarchical MAS orchestration** with role-specialized agents and explicit workflow contracts.
  - Useful case for studying **LLM workflow reliability mechanisms** (timeouts, retries, abandonment recovery, escalation).
  - Demonstrates **human-in-the-loop escalation** in autonomous pipelines via session messaging (`src/installer/step-ops.ts:986-1004`).
  - Shows how multi-agent systems can be built with lightweight infra (YAML + SQLite + cron) rather than heavyweight agent frameworks.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
