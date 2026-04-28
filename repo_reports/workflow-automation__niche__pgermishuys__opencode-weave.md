---
repo_name: pgermishuys/opencode-weave
url: "https://github.com/pgermishuys/opencode-weave"
stars: 122
forks: 6
contributors_count: 6
last_commit_date: "2026-04-21T22:14:26+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T17:58:04.276832+00:00"
model: auto
duration_s: 124.8
clone_size_kb: 22800
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`opencode-weave` is a TypeScript plugin for the OpenCode agent runtime that installs a coordinated team of specialized agents and workflow hooks to automate multi-step software work. A user runs commands like `/start-work` and `/run-workflow`, and the plugin injects structured prompts, switches/targets agents, and tracks execution state across sessions (`src/features/builtin-commands/commands.ts:7-83`, `src/runtime/opencode/plugin-adapter.ts:276-321`). The main experience is: Loom coordinates, Tapestry executes plans, Shuttle does implementation tasks, and Weft/Warp can review outputs. The system persists workflow/work-state to disk and resumes or pauses based on events like idle/interrupt/compaction (`src/features/workflow/engine.ts:31-93`, `src/runtime/opencode/event-router.ts:141-183`). In practice, this is an agentic workflow automation layer over coding tasks, not just a single chatbot prompt pack.

## 2. Agent Framework & Architecture

This repo uses a **custom multi-agent architecture** built on OpenCode’s plugin/SDK interfaces, not LangGraph/LangChain/CrewAI/AutoGen. The primary wiring imports are `@opencode-ai/plugin` and `@opencode-ai/sdk` (`src/index.ts:1`, `src/agents/builtin-agents.ts:1`), and there are no framework imports for LangGraph/LangChain/CrewAI in source.

Architecture-wise, the plugin bootstraps config, hooks, tools, analytics, and an agent registry at startup (`src/index.ts:13-63`). Agents are programmatically created in `createBuiltinAgents`, where models, prompts, category-specialized Shuttle variants, and agent/tool policies are assembled (`src/agents/builtin-agents.ts:180-307`). The intelligence is largely prompt-driven: Loom and Tapestry prompts encode routing/execution logic (`src/agents/loom/prompt-composer.ts:26-292`, `src/agents/tapestry/prompt-composer.ts:22-455`), while runtime policy surfaces enforce behavior at event/tool boundaries (`src/application/orchestration/session-runtime.ts:24-47`).

Operationally, this is a coordinator-worker stack: Loom (primary interface/router), Tapestry (execution orchestrator), Shuttle (leaf worker), plus specialist reviewers (Weft and Warp). Agent mode (`primary`/`subagent`/`all`) controls how they are invoked and model-selection behavior (`src/agents/types.ts:4-17`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)** with event-driven runtime control.

Control flow is explicit in prompts and command routing: `/start-work` is bound to Tapestry, and Tapestry is instructed to delegate every plan task to Shuttle using the Task tool (`src/features/builtin-commands/commands.ts:8-24`, `src/agents/tapestry/prompt-composer.ts:138-181`). Example:

```7:12:src/features/builtin-commands/commands.ts
"start-work": {
  name: "start-work",
  description: "Start executing a Weave plan created by Pattern",
  agent: "tapestry",
```

```23:27:src/agents/tapestry/prompt-composer.ts
Tapestry — coordination orchestrator for Weave.
You coordinate multi-step plans by delegating each task to Shuttle agents, tracking progress, and verifying results.
You do NOT implement work directly.
```

Runtime event handling then applies policy/effects (inject prompt, switch agent, pause execution, analytics) as sessions evolve (`src/runtime/opencode/plugin-adapter.ts:190-218`, `src/runtime/opencode/effects.ts:1-60`, `src/runtime/opencode/event-router.ts:23-184`). This makes it hierarchical orchestration wrapped in an event-driven plugin lifecycle.

## 4. Tools & External Integrations

- **OpenCode plugin runtime and event hooks**: central integration point for chat/tool/command/session events (`src/plugin/plugin-interface.ts:33-47`, `src/runtime/opencode/plugin-adapter.ts:52-312`).
- **Task/subagent delegation tool**: primary mechanism for agent-to-agent delegation (`subagent_type` captured on tool start/end) (`src/runtime/opencode/plugin-adapter.ts:220-274`).
- **Built-in coding tools from OpenCode** (read/edit/write/bash/etc.): Weave does permission/policy filtering, not tool reimplementation (`src/create-tools.ts:31-33`, `src/tools/registry.ts:28-49`).
- **MCP (skill-level)**: `SkillMcpManager` manages stdio MCP processes; HTTP MCP is explicitly unsupported in v1, and stdio call execution is stubbed (`not implemented in v1`) (`src/managers/skill-mcp-manager.ts:20-55`, `:74-76`).
- **Filesystem persistence**: workflow/work-state/execution lease and analytics persisted under workspace storage via FS repositories (`src/features/workflow/engine.ts:40-43`, `src/runtime/opencode/plugin-adapter.ts:16-19`).
- **Git + terminal use by agents**: prompts direct agents to run commands (e.g., `git diff --name-only`) for review workflows (`src/agents/tapestry/prompt-composer.ts:388-397`, `src/agents/warp/default.ts:21-47`).
- **Web fetching in security review prompt guidance**: Warp prompt instructs optional `webfetch` verification for spec confidence (`src/agents/warp/default.ts:105-108`).

## 5. Notable Code Walkthrough

- `src/index.ts:13-63` - Plugin entrypoint; loads config, resolves continuation/hook setup, builds tools/managers/agents, then returns the OpenCode plugin interface. This is the top-level composition root.
- `src/agents/builtin-agents.ts:180-307` - Constructs all built-in agents, resolves models, applies overrides/skills, and dynamically creates category-specific `shuttle-*` workers. This file defines the runtime agent graph surface.
- `src/agents/tapestry/prompt-composer.ts:22-455` - Core execution-orchestrator policy encoded as prompt sections: delegation contracts, parallelism rules, verification gate, error handling, and post-execution review.
- `src/runtime/opencode/plugin-adapter.ts:83-312` - Main runtime adapter for chat/tool/command/events; converts lifecycle events into runtime effects and logs/analytics, including delegation tracing for task tool calls.
- `src/features/workflow/engine.ts:31-220` - Stateful workflow engine (start/check-advance/pause/resume) that injects step prompts and can switch target agents per step.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. The repository automates execution of multi-step plans/workflows by maintaining state, routing tasks to specialist agents, enforcing completion/verification rules, and resuming interrupted sessions (`src/features/builtin-commands/templates/start-work.ts:1-50`, `src/features/workflow/engine.ts:58-174`, `src/runtime/opencode/event-router.ts:164-183`). It is not primarily a RAG system, code generator library, or browser automation tool; those are secondary behaviors inside a broader orchestration engine.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent role separation (coordinator/executor/reviewer) with explicit delegation contracts in prompts (`src/agents/loom/prompt-composer.ts`, `src/agents/tapestry/prompt-composer.ts`).
  - Strong workflow discipline: checklist-driven execution, verification gates, retry/block logic, and continuation semantics.
  - Runtime event policy layer decouples prompt intent from execution effects (`src/application/orchestration/session-runtime.ts:41-46`).
  - Category-aware dynamic worker generation (`shuttle-*`) enables scalable domain specialization (`src/agents/builtin-agents.ts:257-304`).
  - Good observability hooks (delegation, tool usage, token/cost tracking).

- **Limitations:**
  - Heavy reliance on prompt compliance; limited hard guarantees beyond policy hooks.
  - MCP integration is incomplete in v1 (`callTool` for stdio client is unimplemented; HTTP MCP unsupported) (`src/managers/skill-mcp-manager.ts:45-47`, `:74-76`).
  - Complex behavior split across prompts + runtime effects can be difficult to reason about formally.
  - No explicit graph DSL/executor for agent transitions; orchestration semantics are distributed.
  - Security review quality (Warp) depends on prompt-following and heuristic triage, not static-analysis primitives.

- **Research relevance:**
  - Useful evidence of a production-style **prompt-governed manager-worker MAS** in software engineering workflows.
  - Demonstrates hybrid orchestration: hierarchical delegation plus event-driven runtime controls.
  - Shows how policy engines and persisted execution leases can stabilize long-running agent workflows.
  - Good case study for comparing “prompt contract enforcement” vs. “formal planner/graph enforcement” in MAS reliability.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
