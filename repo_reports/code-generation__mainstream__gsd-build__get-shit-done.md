---
repo_name: gsd-build/get-shit-done
url: "https://github.com/gsd-build/get-shit-done"
stars: 56322
forks: 4766
contributors_count: 132
last_commit_date: "2026-04-23T04:26:53+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, Browser / Terminal Use]
generated_at: "2026-04-27T09:21:53.992878+00:00"
model: auto
duration_s: 83.4
clone_size_kb: 13408
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`get-shit-done` is an agentic development orchestration system that users run via `gsd-sdk`/slash-command workflows to drive a full software lifecycle: discuss scope, research, plan, execute, verify, and advance roadmap state. In practice, the user triggers commands like `gsd-sdk auto` (or phase-level workflows), and the system generates/updates planning artifacts (`PLAN.md`, `SUMMARY.md`, `VERIFICATION.md`, roadmap/state files), executes coding tasks, and tracks progress. The core runtime is not just static prompts: it has a TypeScript orchestration engine that repeatedly opens Agent SDK sessions and routes phase state through a deterministic pipeline. It is designed for long-running autonomous project execution with checkpointing, retries, wave-based parallelism, and post-step gates.

## 2. Agent Framework & Architecture

This repo uses **Anthropic Claude Agent SDK** directly, not LangGraph/LangChain/CrewAI/AutoGen. The key runtime import is `query` from `@anthropic-ai/claude-agent-sdk` in `sdk/src/session-runner.ts:8-16`, and sessions are executed by building prompts + tool scopes, then streaming SDK messages to completion (`sdk/src/session-runner.ts:55-99`, `265-300`).

Architecture is a **custom orchestrator + role-specific subagent prompt system**. The orchestrator is implemented in TypeScript (`GSD`, `PhaseRunner`), while specialized roles are defined in markdown agent/workflow specs. `GSD.run()` iterates roadmap phases and invokes `runPhase()` (`sdk/src/index.ts:172-252`), and `PhaseRunner.run()` executes a fixed lifecycle (`discuss -> research -> plan -> plan-check -> execute -> verify -> advance`) with gates and retries (`sdk/src/phase-runner.ts:85-311`).

The “intelligence” is split across:
- **Code-level control logic** (state machine, retries, wave parallelization, gating) in `sdk/src/phase-runner.ts`.
- **Prompt-layer role definitions** in `agents/*.md` and workflow files. These include explicit subagent delegation via `Task(subagent_type="...")` (e.g., planner/researcher/verifier/executor orchestration in `get-shit-done/workflows/plan-phase.md:350-392`, `701-820`; `get-shit-done/workflows/execute-phase.md:421-560`, `1308-1333`).

## 3. Orchestration Pattern

Closest pattern: **hierarchical manager-worker orchestration** (with sequential phase pipeline + intra-phase parallel waves).  
Manager = phase orchestrator prompt + `PhaseRunner`; workers = specialized subagents (`gsd-planner`, `gsd-phase-researcher`, `gsd-executor`, `gsd-verifier`, etc.).

Control flow evidence:
- Deterministic step pipeline in code (`sdk/src/phase-runner.ts:138-279`) that decides when to call LLM sessions, when to retry, and when to halt.
- Worker spawning in workflow prompt instructions (`Task(subagent_type=...)`) that the orchestrator session executes via available tools.

Example 1 (`sdk/src/phase-runner.ts:207-215`):
```text
// ── Step 3: Plan ──
if (!halted) {
  const result = await this.retryOnce('plan', () => this.runStep(PhaseStepType.Plan, phaseNumber, sessionOpts));
  steps.push(result);

  // Re-query to check for plans
  try {
    phaseOp = await this.tools.initPhaseOp(phaseNumber);
```

Example 2 (`get-shit-done/workflows/plan-phase.md:386-391`):
```text
Task(
  prompt=research_prompt,
  subagent_type="gsd-phase-researcher",
  model="{researcher_model}",
  description="Research Phase {phase}"
)
```

## 4. Tools & External Integrations

- **Anthropic Agent runtime** (`@anthropic-ai/claude-agent-sdk`): session execution and streaming via `query(...)` in `sdk/src/session-runner.ts:8-99`, `265-300`.
- **Subagent delegation API (Task tool)**: used in workflow specs to spawn role agents (`get-shit-done/workflows/plan-phase.md`, `execute-phase.md`, `verify-phase.md`).
- **CLI/subprocess bridge to `gsd-tools.cjs` + native query registry**: `sdk/src/gsd-tools.ts:1-11`, `269-360`, `587-595`.
- **Git + shell operations** (branching, commit, tests, worktree workflows) wired in workflow steps, e.g. `get-shit-done/workflows/execute-phase.md:215-218`, `628-631`, `638-758`.
- **WebSocket transport for live event streaming** via `WSTransport` in CLI (`sdk/src/cli.ts:489-496`, `560-567`, `650-656`).
- **Phase-scoped tool permissions** (Read/Write/Edit/Bash/WebSearch/WebFetch by phase) in `sdk/src/tool-scoping.ts:17-24`.
- **Web search/fetch exposure** is explicit in tool scopes (research/planning phases include `WebSearch`/`WebFetch`) at `sdk/src/tool-scoping.ts:18`, `22`.

No vector database or RAG index backend is wired in core runtime code.

## 5. Notable Code Walkthrough

- `sdk/src/phase-runner.ts:91-311` - Core lifecycle state machine with gating logic, retries, verify-loop, and advancement policy; this is the operational backbone.
- `sdk/src/session-runner.ts:55-99` and `265-300` - Unified LLM session execution path using Agent SDK `query`, tool scoping, model/budget control, and stream/result extraction.
- `sdk/src/index.ts:140-252` - High-level orchestration entry points (`runPhase`, `run` milestone loop), including phase rediscovery after each completion.
- `sdk/src/phase-prompt.ts:109-168` and `176-227` - Prompt factory that composes full phase prompts from workflow + agent files + project context, i.e., where role behavior is assembled.
- `get-shit-done/workflows/execute-phase.md:336-760` - Rich manager prompt specifying wave grouping, parallel agent spawning, checkpointing, merge/worktree safety, and post-wave gates.

## 6. Use-Case Mapping

Although this system definitely performs code generation/execution, the primary realized pattern is **Workflow Automation**: it automates an end-to-end SDLC pipeline with explicit phase transitions, gates, retries, artifact management, and milestone progression (`sdk/src/phase-runner.ts`, `sdk/src/index.ts`). Code generation is one component within a larger autonomous workflow controller (research/planning/verification/state updates/roadmap transitions). So the upstream “Code Generation” label is incomplete; this repo is better categorized as **Workflow Automation** with code-gen workers.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong explicit orchestration logic (state machine + retries + gates) rather than opaque “agent magic” (`sdk/src/phase-runner.ts`).
  - Clear role separation across planner/researcher/executor/verifier with dedicated prompts and tool scopes.
  - Practical production concerns handled (worktree merge safety, checkpoint recovery, fallback behaviors) in `execute-phase.md`.
  - Supports autonomous and human-gated modes, including callback hooks and verification decision branches.
  - Rich observability/event model (phase/step/wave/cost events) via event stream + transports.

- **Limitations:**
  - Heavy behavior encoded in huge markdown workflow prompts; maintainability and formal verification are difficult.
  - Runtime correctness depends on prompt-following reliability of LLM/tool behavior (especially Task orchestration semantics).
  - Tight coupling to Anthropic Agent SDK and Claude-style tooling assumptions.
  - Limited typed enforcement of prompt contracts; many guarantees are convention-level.
  - Extensive shell-driven operations in prompts can be brittle across environments.

- **Research relevance:**
  - Strong case study of **hierarchical multi-agent orchestration** over real software tasks.
  - Demonstrates hybrid control: symbolic state machine in code + natural-language policies in prompts.
  - Useful evidence for studying **agent reliability engineering** (fallbacks, retries, gates, human checkpoints).
  - Illustrates practical phase-based decomposition and wave parallelism in multi-agent software development.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
