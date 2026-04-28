---
repo_name: HKUDS/ClawTeam
url: "https://github.com/HKUDS/ClawTeam"
stars: 4922
forks: 669
contributors_count: 29
last_commit_date: "2026-04-15T13:12:36+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T13:19:47.430643+00:00"
model: auto
duration_s: 93.5
clone_size_kb: 19960
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

ClawTeam is a Python CLI framework for running multiple coding agents as a coordinated team, rather than a single assistant. A user runs commands like `clawteam harness conduct ...`, `clawteam run ...`, and `clawteam spawn ...` to create teams, launch role-specific workers, and drive work through shared tasks, inboxes, and workspaces (`clawteam/cli/commands.py:4428-4474`, `4479-4587`). The system persists team state on disk, routes inter-agent messages, and can isolate each agent in its own git worktree (`clawteam/team/manager.py:78-113`, `clawteam/workspace/manager.py:65-177`). In practice, users get “one-command” orchestration of planning, implementation, and verification loops across several LLM coding CLIs.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen as a runtime dependency; the orchestration is largely **custom** Python, with Typer CLI + Pydantic models + custom event bus and spawn backends (`pyproject.toml:21-28`; no framework imports in core orchestration files). It does use the MCP Python SDK (`mcp.server.fastmcp.FastMCP`) to expose ClawTeam operations as MCP tools (`clawteam/mcp/server.py:8-33`).

Architecture is role-and-phase based: planner/executor/evaluator roles are defined in `DEFAULT_ROLES` with role-specific prompt add-ons (`clawteam/harness/roles.py:24-51`), and the run state is managed as phases (`discuss -> plan -> execute -> verify -> ship`) with gates (`clawteam/harness/phases.py:22-37`, `64-104`). `HarnessOrchestrator` stores state/artifacts and advances phases, while `HarnessConductor` runs a polling loop that spawns agents, checks exits, triggers phase transitions, and prepares execution tasks from contracts (`clawteam/harness/orchestrator.py:21-78`; `clawteam/harness/conductor.py:83-151`, `153-173`).

“Intelligence” is split across: (1) injected system prompts for agent behavior (`clawteam/harness/prompts.py:6-38`), (2) phase gates and artifact checks (`clawteam/harness/phases.py:106-160`), and (3) contract-to-task translation/assignment (`clawteam/harness/contract_executor.py:56-99`). The LLM inference itself is delegated to external CLIs (Claude/Codex/Gemini/etc.) through adapter/backends (`clawteam/spawn/adapters.py:31-146`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with phase-state workflow**, plus event-driven hooks.

- Manager/worker: `HarnessConductor` + `HarnessOrchestrator` act as control plane; role workers are spawned per phase (`clawteam/harness/conductor.py:97-133`, `clawteam/harness/spawner.py:20-99`).
- State machine: `PhaseRunner` enforces gate-checked transitions between ordered phases (`clawteam/harness/phases.py:126-160`).
- Event layer: plugins/hooks subscribe to typed events but do not replace central control (`clawteam/events/bus.py:42-107`).

Example control flow excerpt 1:

```97:133:clawteam/harness/conductor.py
# Initial spawn for current phase
spawned = self._spawn.spawn_for_phase(
    self._orch.state.current_phase, self._orch,
)
...
new_phase = self._orch.advance()
if new_phase:
    ...
    spawned = self._spawn.spawn_for_phase(new_phase, self._orch)
```

Example control flow excerpt 2:

```126:160:clawteam/harness/phases.py
def advance(self) -> str | None:
    ok, reason = self.can_advance()
    if not ok:
        return None
    ...
    old_phase = self.state.current_phase
    new_phase = phases[idx + 1]
    self.state.current_phase = new_phase
```

## 4. Tools & External Integrations

- **LLM coding CLIs (Claude, Codex, Gemini, Kimi, Qwen, OpenCode, Nanobot, etc.)**: normalized and runtime-adapted in `clawteam/spawn/adapters.py:31-237`; invoked by spawn backends.
- **Terminal/session orchestration**:
  - `tmux` backend for interactive workers (`clawteam/spawn/tmux_backend.py:45-317`).
  - `wsh`/WaveTerminal backend (`clawteam/spawn/wsh_backend.py:205-412`).
  - headless subprocess backend (`clawteam/spawn/subprocess_backend.py:29-153`).
- **MCP server/tools**: FastMCP server and tool registry (`clawteam/mcp/server.py:13-33`, `clawteam/mcp/tools/__init__.py:28-55`), including team/task/mailbox/plan/board/workspace operations.
- **Filesystem-backed messaging + optional P2P transport**:
  - file transport for inbox delivery (`clawteam/transport/file.py:102-259`);
  - ZeroMQ PUSH/PULL with file fallback (`clawteam/transport/p2p.py:28-220`).
- **Git worktree automation** for isolated agent branches/workspaces (`clawteam/workspace/manager.py:65-177`, `252-283`).
- **Plugin/event integration** via dynamic plugin loading + event bus (`clawteam/plugins/manager.py:21-137`; `clawteam/events/types.py:24-195`).
- **No vector DB / embedding RAG stack found** in core runtime code.

## 5. Notable Code Walkthrough

- `clawteam/harness/conductor.py:42-175` - Main runtime loop that actually conducts multi-agent execution: spawns role workers, watches exits, advances phases, and creates execution tasks from contracts.
- `clawteam/harness/phases.py:39-193` - Defines persisted phase state + gate logic (`ArtifactRequiredGate`, `AllTasksCompleteGate`, `HumanApprovalGate`), which is the backbone of orchestration correctness.
- `clawteam/harness/spawner.py:20-99` - Converts phase/role configuration into concrete agent processes, registers team members, injects harness prompts, and calls backend spawn.
- `clawteam/spawn/tmux_backend.py:45-317` - Representative spawn backend showing how external LLM CLIs are launched with environment wiring, prompt injection, lifecycle hooks, and agent registry updates.
- `clawteam/mcp/tools/__init__.py:28-55` - Compact manifest of operations exposed to MCP clients; demonstrates that ClawTeam is not only CLI-driven but also tool-callable as orchestration infrastructure.

## 6. Use-Case Mapping

Although this repository supports code-writing workers, the core product is broader orchestration infrastructure: team lifecycle, phased workflows, task routing, inbox communication, spawn backends, and worktree management. The harness explicitly coordinates a full process (`discuss/plan/execute/verify/ship`) rather than just generating code text (`clawteam/harness/phases.py:22-37`, `clawteam/cli/commands.py:4428-4474`). So the upstream “Code Generation” label is understandable but too narrow. A better primary category is **Workflow Automation**, with code generation as one important workload.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear runtime separation between orchestration control plane and worker CLIs (`orchestrator`/`conductor` vs `spawn` backends).
  - Practical multi-agent ops features: task store, inbox transports, workspace isolation, lifecycle hooks.
  - Flexible role/phase model with gates and artifact-driven progression (`phases.py`).
  - Multi-runtime support (tmux, wsh, subprocess) makes coordination portable.
  - MCP exposure enables integration into broader agent/tool ecosystems.

- **Limitations:**
  - Heavy reliance on polling loops and best-effort exception swallowing in key paths can mask failures (`except Exception: pass` appears in orchestration/spawner/plugin paths).
  - LLM reasoning/planning quality is delegated to external CLIs; little internal model-agnostic planning logic beyond prompt templates.
  - No formal conflict-resolution or consensus mechanism among peer agents; control remains centralized.
  - No native long-term semantic memory / vector retrieval layer in core architecture.
  - Reliability depends on external terminal tooling (`tmux`, `wsh`) and CLI behaviors that may vary across environments.

- **Research relevance:**
  - Evidence of a production-oriented **manager-worker multi-agent architecture** built around operational tooling, not just toy chat agents.
  - Useful case for studying **phase-gated agent workflows** with explicit human approval gates.
  - Illustrates hybrid communication designs (shared filesystem inbox + optional P2P transport fallback).
  - Demonstrates integration pattern where LLM capability is outsourced to heterogeneous agent CLIs under one orchestration layer.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
