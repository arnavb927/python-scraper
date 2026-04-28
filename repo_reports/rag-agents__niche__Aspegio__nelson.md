---
repo_name: Aspegio/nelson
url: "https://github.com/Aspegio/nelson"
stars: 318
forks: 28
contributors_count: 6
last_commit_date: "2026-04-21T12:04:41+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:33:40.829265+00:00"
model: auto
duration_s: 75.9
clone_size_kb: 1841
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`Aspegio/nelson` is not an LLM app that runs its own model inference; it is a **Claude Code skill/plugin** that imposes a strict operating procedure for multi-agent coding missions. A user installs the plugin, says “Use Nelson to…”, and Claude follows an 8-step workflow (sailing orders, estimate, battle plan, squadron formation, permission gate, checkpoints, quality gates, stand-down) defined in `skills/nelson/SKILL.md`. The repo’s Python code provides enforcement and state tracking: hooks block invalid tool usage, CLI scripts persist mission artifacts in `.nelson/missions/...`, and analytics scripts summarize outcomes across missions. The output a user gets is operational structure (task plans, logs, checkpoints, handoff packets, validations), not a standalone chatbot or RAG API.

## 2. Agent Framework & Architecture

This repo uses a **custom orchestration layer on top of Claude Code’s native agent tools**, not LangGraph/LangChain/CrewAI/AutoGen. I found no imports of those frameworks (`rg` over codebase returned no matches), while the skill explicitly targets Claude tool primitives (`Agent`, `TeamCreate`, `TaskCreate`, `SendMessage`) in `skills/nelson/references/tool-mapping.md:7-47` and hooks them in `hooks/hooks.json:3-53`.

Architecture is split between:
- **Prompt/protocol layer**: `skills/nelson/SKILL.md` defines behavior, role hierarchy (admiral/captains/crew), and when to spawn subagents (`skills/nelson/SKILL.md:129-214`).
- **Deterministic control/state layer**: Python scripts store mission state in JSON, enforce phase transitions, and run preflight/quality checks (`skills/nelson/scripts/nelson-phase.py:44-67`, `skills/nelson/scripts/nelson_data_lifecycle.py:63-153`, `hooks/nelson_hooks.py:202-223`).

“Intelligence” mainly lives in the skill instructions and templates; Python code is mostly guardrails, schema validation, and telemetry, not planning or reasoning logic.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) orchestration with phase-gated workflow automation**.

- The **admiral** coordinates; **captains/subagents** execute tasks depending on selected mode (`single-session`, `subagents`, `agent-team`) in `skills/nelson/SKILL.md:131-139` and `skills/nelson/references/tool-mapping.md:26-47`.
- Control flow is linear by mission phase (SAILING_ORDERS -> … -> STAND_DOWN), enforced by `nelson-phase.py` validators and blocked tools.

Example 1 (phase machine + blocked tools): `skills/nelson/scripts/nelson-phase.py:44-66`
```python
PHASES = (
    "SAILING_ORDERS", "ESTIMATE", "BATTLE_PLAN",
    "FORMATION", "PERMISSION", "UNDERWAY", "STAND_DOWN",
)
BLOCKED_TOOLS: dict[str, frozenset[str]] = {
    "SAILING_ORDERS": frozenset({"Agent", "TeamCreate", "TaskCreate"}),
    "ESTIMATE": frozenset({"TeamCreate", "TaskCreate"}),
    ...
}
```

Example 2 (hooked preflight gate before spawning agents): `hooks/nelson_hooks.py:213-221`
```python
for check in (
    lambda: _check_station_tiers(tasks),
    lambda: _check_file_ownership(tasks),
    lambda: _check_mode_tool_consistency(_get_mode(battle_plan), tool_input),
):
    msg = check()
    if msg:
        _reject(msg)
```

## 4. Tools & External Integrations

- **Claude Code agent/team/task messaging primitives** (`Agent`, `TeamCreate`, `TaskCreate`, `TaskUpdate`, `TaskList`, `SendMessage`) are the primary integration surface, mapped by mode in `skills/nelson/references/tool-mapping.md:7-53`.
- **Claude hook system** integrates enforcement at tool events via `hooks/hooks.json:3-53` calling `hooks/nelson_hooks.py`.
- **Filesystem artifact store** under `.nelson/` for mission state, logs, handoff packets, and analytics (`skills/nelson/scripts/nelson_data_lifecycle.py:92-151`).
- **Git CLI integration** for conflict radar (`git status --porcelain -z`) in `skills/nelson/scripts/nelson_conflict_radar.py:45-51`.
- **Local subprocess integration** to run conflict scan from lifecycle flow (`subprocess.run(...)`) in `skills/nelson/scripts/nelson_data_lifecycle.py:1495-1503`.
- **No external LLM API, vector DB, web search, browser automation, or RAG pipeline** is wired in code; scripts are stdlib-only (`No external dependencies` comments in multiple script headers).

## 5. Notable Code Walkthrough

- `skills/nelson/SKILL.md:18-325` — The core operational doctrine: defines 8-step mission lifecycle, role semantics, approval gates, and when/how agents are spawned. This is where most multi-agent behavior is specified.
- `hooks/nelson_hooks.py:202-223` and `:481-508` — Runtime policy engine: blocks unsafe agent spawns and enforces station-tier completion evidence before task completion.
- `skills/nelson/scripts/nelson-phase.py:421-471` — Deterministic phase transition engine; validates exit criteria and logs phase transitions, preventing out-of-order execution.
- `skills/nelson/scripts/nelson_data_lifecycle.py:1512-1578` — Composite `form` flow that registers tasks, forms squadron, computes DAG metrics, and runs conflict scan in one command.
- `skills/nelson/scripts/nelson_circuit_breakers.py:106-131` and `:347-409` — Automated mission health checks (budget, hull integrity, consecutive blockers, idle timeout) used for quarterdeck advisories.

## 6. Use-Case Mapping

The upstream label `RAG + Agents` looks incorrect for the actual code. Nelson does implement multi-agent coordination, but it does **not** implement retrieval-augmented generation in the typical sense (no embeddings, retriever, vector index, retrieval pipeline into prompts). Its “memory” features are mission analytics over JSON artifacts (`index/history/brief/analytics`), not document retrieval for answer generation (`skills/nelson/scripts/nelson_data_fleet.py:55-115`, `:534-556`).

A better category is **Workflow Automation**: the repo formalizes and automates agent mission lifecycle, governance, quality gates, and operational telemetry around coordinated agents.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong runtime governance via hooks and phase gates, not just prompt advice (`hooks/nelson_hooks.py`, `settings.json` hook to `nelson-phase.py`).
  - Clear hierarchical multi-agent operating model with explicit mode switching (`single-session` / `subagents` / `agent-team`).
  - Rich mission observability artifacts (`fleet-status.json`, `mission-log.json`, checkpoints, handoff packets).
  - Built-in safety controls (station tiers, rollback/failure evidence checks, circuit-breaker advisories).
  - Portable implementation (stdlib Python, minimal infra assumptions).

- **Limitations:**
  - Heavy dependence on Claude Code semantics/tools; limited portability to other agent runtimes.
  - Intelligence is instruction-centric; little algorithmic autonomy/planning beyond deterministic checks.
  - Conflict detection is heuristic (regex import parsing, global git diff) and can miss complex dependency issues.
  - No integrated execution sandbox or automatic remediation when breakers trip (advisory-only in current design).
  - Not a general MAS library/API; it is a framework/procedure layer for one host environment.

- **Research relevance:**
  - Good evidence of **governed multi-agent orchestration** (policy enforcement + phase transitions + human gates).
  - Useful case study for **operational reliability patterns** in agent teams (handoff, checkpointing, failure procedures).
  - Demonstrates how **human organizational metaphors** can structure agent coordination with measurable artifacts.
  - Relevant to studies on **runtime controls vs prompt-only controls** in practical agent deployments.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
