---
repo_name: dnnyngyen/iron-manus-mcp
url: "https://github.com/dnnyngyen/iron-manus-mcp"
stars: 65
forks: 11
contributors_count: 3
last_commit_date: "2026-02-16T09:23:32+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 0
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T18:15:52.328457+00:00"
model: auto
duration_s: 86.3
clone_size_kb: 4216
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`iron-manus-mcp` is a TypeScript MCP server that exposes a workflow controller (`JARVIS`) and supporting tools for API research, Python-oriented computation, state tracking, and slide generation. A user runs the server (`npm run build && npm start`) and connects it as an MCP server so an LLM client can call these tools during task execution (`src/index.ts:23-281`, `README.md:108-149`). The core problem it solves is structured long-horizon automation: instead of ad-hoc tool use, it enforces an 8-phase loop (`INIT → QUERY → ENHANCE → KNOWLEDGE → PLAN → EXECUTE → VERIFY → DONE`) with role-aware prompting and verification logic (`src/phase-engine/FSM.ts:247-452`). In practice, users get a guided orchestration layer that pushes planning, delegates subtasks, and tracks progress/session state across steps.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex in code imports. It is a **custom agent orchestration framework** built on the Model Context Protocol SDK (`@modelcontextprotocol/sdk`) (`package.json:30-41`, `src/index.ts:23-26`).

Architecture is centered on one manager agent interface (`JARVIS` tool) that drives a custom finite-state machine and emits phase-specific system prompts plus allowed tools (`src/tools/orchestration/jarvis-tool.ts:22-83`, `src/phase-engine/FSM.ts:412-449`). The “intelligence” is distributed between:
- prompt-generation logic (role selection prompts, phase prompts, role methodologies) (`src/core/prompts.ts:237-336`, `src/core/prompts.ts:666-867`);
- FSM transition/rollback logic (`src/phase-engine/FSM.ts:289-410`, `src/phase-engine/FSM.ts:881-920`);
- tool-level procedural agents such as `APITaskAgent` (`src/tools/api/api-task-agent.ts:62-447`).

State is persisted as a session graph (entities/relations) in per-session files under `iron-manus-sessions`, accessed via an adapter to preserve FSM session semantics (`src/tools/orchestration/iron-manus-state-graph.ts:201-292`, `src/core/graph-state-adapter.ts:21-102`). The code also explicitly designs for delegated subagents through `Task()` conventions encoded in prompts/todos, though those Task agents are expected to be provided by the host LLM runtime, not implemented as local worker processes in this repo (`src/core/prompts.ts:808-845`, `src/phase-engine/FSM.ts:1254-1291`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with FSM gating**.

- Manager: `JARVIS`/FSM controls global phase transitions and tool permissions.
- Workers: delegated `Task()` agents and specialized tools perform subtasks.
- Control style: deterministic phase machine + prompt-driven delegation (not peer swarm).

Code evidence of deterministic phase control:

```289:299:src/phase-engine/FSM.ts
switch (session.current_phase) {
  case 'INIT':
    nextPhase = 'QUERY';
    break;
  case 'QUERY':
    if (input.phase_completed === 'QUERY') {
      // Parse Claude's role selection
```

Code evidence of phase-gated tool routing:

```1342:1356:src/core/prompts.ts
export const PHASE_ALLOWED_TOOLS: Record<Phase, string[]> = {
  INIT: ['JARVIS'],
  QUERY: ['JARVIS'],
  ENHANCE: ['JARVIS'],
  KNOWLEDGE: ['Task', 'WebSearch', 'WebFetch', 'APITaskAgent', ...],
  PLAN: ['TodoWrite'],
  EXECUTE: ['TodoRead', 'TodoWrite', 'Task', 'Bash', ...],
```

## 4. Tools & External Integrations

- **MCP server runtime** via `@modelcontextprotocol/sdk`, stdio transport (`src/index.ts:23-25`, `src/index.ts:279-281`).
- **External HTTP APIs** via `axios` for fetch/validation with retries and rate limiting (`src/utils/api-fetcher.ts:6-114`, `src/utils/api-fetcher.ts:117-244`).
- **Large API catalog (63+)** in `SAMPLE_API_REGISTRY`, used for role-based API selection (`src/core/api-registry.ts:100-909`, `src/core/api-registry.ts:1232-1266`).
- **Auto-connection knowledge pipeline** (fetch + synthesize) using `axios` + `p-limit` (`src/knowledge/autoConnection.ts:3-10`, `src/knowledge/autoConnection.ts:317-364`).
- **Python execution integration**: generates Python code and instructs host-side `mcp__ide__executeCode` execution (Jupyter kernel assumption) (`src/tools/computation/python-computational-tool.ts:168-179`).
- **Filesystem session workspace** (`iron-manus-sessions/<session_id>`) for state graphs and inter-agent artifacts (`src/tools/orchestration/iron-manus-state-graph.ts:207-209`, `src/phase-engine/FSM.ts:493-500`).
- **HTML slide generation** persisted to session folders (`src/tools/content/slide-generator-tool.ts:431-459`).
- **Security layer**: SSRF URL sanitization, host/rate limits, config validation (`src/knowledge/autoConnection.ts:78-95`, `src/utils/api-fetcher.ts:157-163`, `src/config.ts:334-382`).
- **Host-provided tools expected by prompts** (`Task`, `WebSearch`, `WebFetch`, `TodoWrite`, `Bash`, etc.) are referenced in allowed-tool configs, but implemented externally by the LLM environment (`src/core/prompts.ts:1342-1370`).

## 5. Notable Code Walkthrough

- `src/phase-engine/FSM.ts:247-452` - Core runtime brain: handles session load, role initialization, per-phase transitions, prompt generation, and output payload assembly.
- `src/core/prompts.ts:666-867` - Defines the operational behavior per phase, including delegation protocols (parallel research/execution patterns and Task-agent conventions).
- `src/tools/api/api-task-agent.ts:126-223` - Implements a concrete “worker agent” tool that orchestrates discovery → validation → fetch → synthesis in one call.
- `src/core/graph-state-adapter.ts:87-200` - Bridges FSM session objects to persisted graph entities/tasks, enabling cross-turn continuity.
- `src/tools/orchestration/iron-manus-state-graph.ts:145-292` - Implements low-level graph persistence and safe session-scoped storage backing the orchestration memory.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** is accurate. The repo operationalizes workflow automation through a fixed multi-phase control loop, gated tool permissions by phase, and explicit planning/execution/verification checkpoints (`src/phase-engine/FSM.ts:289-410`, `src/core/prompts.ts:1342-1395`). It automates decomposition and coordination of complex objectives into ordered tasks (including optional delegated subagents), then loops until verification criteria are met or rollback is triggered (`src/phase-engine/FSM.ts:821-920`). Although it includes API/data and slide-generation capabilities, these are subordinate to the orchestration workflow rather than being the primary product category.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong explicit control structure (8-phase FSM + rollback logic) instead of opaque agent loops (`src/phase-engine/FSM.ts:289-410`, `src/phase-engine/FSM.ts:881-920`).
  - Clear phase-based tool governance that reduces unsafe or off-protocol actions (`src/core/prompts.ts:1342-1370`).
  - Practical security hardening for external calls (SSRF, rate limiting, size/time limits) (`src/security/ssrfGuard.ts`, `src/utils/api-fetcher.ts:128-133`).
  - Session persistence model supports long-running workflows and traceability (`src/tools/orchestration/iron-manus-state-graph.ts:245-292`).
  - Modular MCP tool registry makes orchestration extensible (`src/tools/tool-registry.ts:38-45`).

- **Limitations:**
  - Multi-agent delegation (`Task()`) is mostly prompt/protocol-driven and depends on host runtime behavior, not enforced internal worker orchestration (`src/core/prompts.ts:808-845`).
  - “Claude-powered” role/API selection parsing relies on fenced JSON in model text, which is brittle (`src/core/prompts.ts:357-397`, `src/core/api-registry.ts:1352-1390`).
  - Some knowledge auto-connection uses fixed sample URLs, limiting objective-specific retrieval fidelity (`src/knowledge/autoConnection.ts:330-335`).
  - State adapter repeatedly appends observations; graph can grow noisily without compaction (`src/core/graph-state-adapter.ts:165-187`).
  - Prompt layer is very large and policy-heavy, increasing maintenance burden and prompt drift risk (`src/core/prompts.ts:666-1503`).

- **Research relevance:**
  - Good case study of **deterministic FSM governance over LLM behavior** in agentic systems.
  - Illustrates a **hybrid architecture**: symbolic state machine + prompt-based subagent delegation.
  - Demonstrates **phase-gated tool permissions** as an interpretable alignment/control mechanism.
  - Useful evidence for **file-backed inter-agent coordination** in constrained-context environments.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
