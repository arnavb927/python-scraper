---
repo_name: parcadei/Continuous-Claude-v3
url: "https://github.com/parcadei/Continuous-Claude-v3"
stars: 3729
forks: 286
contributors_count: 14
last_commit_date: "2026-01-26T15:27:42+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, Browser / Terminal Use]
generated_at: "2026-04-27T13:39:57.926464+00:00"
model: auto
duration_s: 120.8
clone_size_kb: 8284
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`Continuous-Claude-v3` is an opinionated runtime layer on top of Claude Code that turns a single assistant into a persistent, hook-driven multi-agent workflow system. In practice, a user runs Claude Code with this repo’s installed `.claude` config; hooks then auto-inject skill recommendations, route search/context tooling, spawn specialized subagents, and persist state across sessions. The system’s core value is continuity and orchestration: it tracks sessions, file claims, agent status, memory, and handoffs so long tasks can be split across agents and resumed safely. Users get automated workflow scaffolding (plan/build/fix/review/release flows), not just raw chat.

## 2. Agent Framework & Architecture

This is **not LangGraph/LangChain/CrewAI/AutoGen** in the checked-in runtime path. It is a **custom orchestration framework** built around Claude Code primitives (Task/subagent hooks, agent markdown profiles, skill rules, and hook middleware). Evidence: hook and spawn logic is implemented directly in TypeScript/Python (`.claude/hooks/src/*.ts`, `opc/scripts/claude_spawn.py`), with no LangGraph/CrewAI imports in active orchestration files; routing is regex/rule-based (`opc/scripts/claude_spawn.py:334-365`, `.claude/hooks/src/skill-activation-prompt.ts:257-373`).

Architecture is layered:
- **Skill activation/routing**: user prompts are matched to skill and agent suggestions (`.claude/hooks/src/skill-activation-prompt.ts:231-311`), including optional pattern inference and semantic query hints.
- **Agent runtime**: agents are represented as profiles/prompts (`.claude/agents/*.md`) and spawned headlessly via `claude -p` with depth/limit controls (`opc/scripts/claude_spawn.py:653-754`, `877-969`).
- **Pattern-aware coordination hooks**: lifecycle hooks track and coordinate swarm/hierarchical/pipeline/jury/etc. patterns (`.claude/hooks/dist/subagent-start.mjs`, `.claude/hooks/dist/subagent-stop.mjs`, `.claude/hooks/src/patterns/*.ts`).
- **Persistence/memory**: PostgreSQL/SQLite-backed session coordination, memory recall, handoff indexing, and background extraction (`.claude/hooks/src/shared/db-utils-pg.ts`, `.claude/scripts/core/memory_daemon.py`).

The “intelligence” lives mostly in **prompt engineering + hook policies + pattern handlers**, not a central planner graph class.

## 3. Orchestration Pattern

Closest match: **hybrid hierarchical + event-driven orchestration** (with optional swarm/pipeline/map-reduce variants).

- **Hierarchical manager-worker**: coordinator/specialist semantics are explicit, with completion gating and synthesis prompts (`.claude/hooks/src/patterns/hierarchical.ts:75-93`, `389-509`).
- **Event-driven hook bus**: orchestration is triggered by Claude lifecycle events (`SessionStart`, `PreToolUse`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `Stop`) configured in `.claude/settings.json:6-275`.

Short control-flow excerpts:

```390:508:.claude/hooks/src/patterns/hierarchical.ts
if (data.completed < data.total) {
  return {
    result: 'block',
    message: `Waiting for ${waiting} specialist(s)...`
  };
}
message += '\nSynthesize the specialist results...';
return { result: 'continue', message };
```

```523:574:.claude/hooks/dist/subagent-start.mjs
const pattern = detectPattern() || "task";
switch (pattern) {
  case "swarm": output = await onSubagentStart(input); break;
  case "pipeline": output = await onSubagentStart11(input); break;
  case "hierarchical": output = await onSubagentStart3(input); break;
  // ...other patterns...
}
```

## 4. Tools & External Integrations

- **Claude CLI headless subagents** via `claude -p` spawn calls (`opc/scripts/claude_spawn.py:521-546`, `724-730`).
- **Claude hook system** (core orchestration substrate), wired in `.claude/settings.json:6-275`.
- **TLDR code-analysis daemon/CLI** for AST/callgraph/CFG/DFG/PDG context injection (`.claude/hooks/src/tldr-context-inject.ts:220-392`).
- **PostgreSQL + asyncpg/psycopg2** for session/agent/file-claim/blackboard-like coordination (`.claude/hooks/src/shared/db-utils-pg.ts:33-91`, `390-445`; `.claude/scripts/core/memory_daemon.py:93-133`).
- **SQLite fallback/state stores** for pattern tables and local coordination in hook handlers (`.claude/hooks/src/patterns/pipeline.ts:261-301`; `.claude/hooks/dist/subagent-stop.mjs:151-193`).
- **MCP servers** configured for git/fetch/qlty plus optional GitHub/Firecrawl/Morph/Perplexity/Nia/ast-grep/repoprompt (`.claude/mcp_config.json:2-76`).
- **Braintrust tracing hooks** integrated as shell hooks (`.claude/settings.json:101-102`, `214-215`, `270-271`).
- **Memory extraction daemon** spawning headless Claude to mine past sessions (`.claude/scripts/core/memory_daemon.py:260-274`).

## 5. Notable Code Walkthrough

- `.claude/settings.json:6-275` — Central runtime wiring for all lifecycle hooks; this is effectively the system’s control plane.
- `.claude/hooks/src/skill-activation-prompt.ts:248-490` — Prompt-to-skill/agent inference and activation output; it is the primary router from natural language intent to workflow behavior.
- `opc/scripts/claude_spawn.py:653-754` — Core subagent spawn engine with depth limits, process tracking, profile loading, and DB registration.
- `.claude/hooks/src/patterns/hierarchical.ts:285-383` — Tracks specialist spawns/completions and enforces synthesis readiness; concrete manager-worker mechanics.
- `.claude/hooks/src/patterns/pipeline.ts:329-345` — Sequential stage progression with optional auto-spawn of next stage and upstream artifact/context chaining.

## 6. Use-Case Mapping

Although the repo can support coding tasks, its implementation is primarily a **workflow automation system for AI-assisted development operations** (routing, orchestration, lifecycle hooks, persistence, memory, coordination), rather than a focused code-generation engine itself.

Why: most core code is about **agent coordination and stateful process automation** (`.claude/settings.json`, hook pattern handlers, spawn/memory/session DB machinery), while code generation is one downstream workflow among many (`kraken`, `spark`, etc.). So the upstream assigned label `Code Generation` is understandable but incomplete; **`Workflow Automation`** is a better top-level fit.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong real-world orchestration substrate using lifecycle hooks as event triggers (`.claude/settings.json`).
  - Multiple explicit MAS patterns (hierarchical, swarm, jury, pipeline, map-reduce, adversarial, etc.) in runnable handlers (`.claude/hooks/src/patterns/*`).
  - Persistent coordination primitives (sessions, file claims, active agent counts, memory recall) built into runtime (`.claude/hooks/src/shared/db-utils-pg.ts`).
  - Good context-efficiency strategy via TLDR injection before agent tasks (`.claude/hooks/src/tldr-context-inject.ts`).

- **Limitations:**
  - Some runtime links point to modules not present in this clone (e.g., `scripts.agentica_patterns.*` imports in hook bridge/spawn code), suggesting coupling to installed/global layout.
  - Heavy reliance on environment/config correctness; many features degrade silently when paths/services are missing (`.claude/hooks/src/shared/opc-path.ts`).
  - Pattern logic is distributed across many hook files and compiled artifacts, increasing maintenance complexity.
  - Safety/policy behavior is largely prompt/rule-driven, not formally verified scheduler logic.

- **Research relevance:**
  - Useful evidence of **hook-driven event orchestration** as an alternative to graph frameworks for MAS.
  - Demonstrates practical **manager-worker + pattern-polymorphic coordination** in developer tooling.
  - Shows integration of **persistent memory/continuity** with multi-agent coding workflows.
  - Relevant as a case study in **agent operations engineering** (limits, tracking, lifecycle monitoring, graceful degradation).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
