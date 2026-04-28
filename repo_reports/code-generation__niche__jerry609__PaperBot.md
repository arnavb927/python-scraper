---
repo_name: jerry609/PaperBot
url: "https://github.com/jerry609/PaperBot"
stars: 103
forks: 12
contributors_count: 10
last_commit_date: "2026-03-19T15:46:15+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T15:50:19.744573+00:00"
model: auto
duration_s: 96.2
clone_size_kb: 192852
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`PaperBot` is a FastAPI-based “academic AI infrastructure” that exposes multiple SSE endpoints for research tracking, paper analysis, and paper-to-code workflows. In practice, users run the backend API (plus optional web/CLI frontends) and trigger flows like `POST /api/gen-code` or `/api/agent-board/*`, which execute multi-step agent pipelines and stream progress/results. The system ingests paper/context data, decomposes work into tasks, generates or edits code in sandboxed environments, verifies/repairs outputs, and stores run/session telemetry. It is not just a chatbot wrapper: the codebase implements explicit multi-agent coordination, task scheduling, and tool-driven execution loops. The result users get is reproducible code artifacts, verification status, and persisted run/task state for iterative automation.

## 2. Agent Framework & Architecture

This repo is **not** built on LangGraph/LangChain/CrewAI/AutoGen as primary runtime frameworks. The core runtime is **custom orchestration** with direct SDK calls to Anthropic/OpenAI (`anthropic.AsyncAnthropic`, `openai.AsyncOpenAI`) and project-specific agent classes (`src/paperbot/repro/orchestrator.py:21-29`, `src/paperbot/infrastructure/swarm/claude_commander.py:75-113`, `src/paperbot/infrastructure/swarm/codex_dispatcher.py:239-261`).

Two major agentic architectures coexist:

1. **Paper2Code orchestrator path** (`/api/gen-code`): `ReproAgent` optionally enables a multi-agent orchestrator with specialized roles (Planning, Coding, Verification, Debugging) and a repair loop (`src/paperbot/repro/repro_agent.py:268-277`, `src/paperbot/repro/orchestrator.py:117-126`, `src/paperbot/repro/orchestrator.py:281-332`).  
2. **Agent Board swarm path** (`/api/agent-board`): a manager-worker setup where Claude decomposes work into tasks and Codex workers execute those tasks with tool-calling inside a shared sandbox, then verification/review updates task lifecycle (`src/paperbot/api/routes/agent_board.py:25-46`, `src/paperbot/infrastructure/swarm/agents/planner.py:35-57`, `src/paperbot/infrastructure/swarm/agents/executor.py:57-91`).

“Intelligence” is distributed across prompt-building methods and runtime controllers: decomposition/review prompts in `ClaudeCommander`, CodeAct-style tool-loop policy in `CodexDispatcher`, and stage/repair logic in `Orchestrator`.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker + DAG-batched workflow automation** (with event-driven streaming around it).

- Manager-worker: Claude/planner decomposes, Codex/executor implements, then verification/review gates status transitions (`src/paperbot/infrastructure/swarm/claude_commander.py:63-96`, `src/paperbot/infrastructure/swarm/agents/executor.py:52-65`).
- DAG batches: tasks are topologically grouped and run concurrently when dependency-safe (`src/paperbot/infrastructure/swarm/task_dag.py:30-57`, `src/paperbot/api/routes/agent_board.py:1294-1338`).
- Sequential stage machine with loops: Paper2Code runs planning→coding→verification and loops debugging until pass/limit (`src/paperbot/repro/orchestrator.py:252-332`).

Example control flow excerpt (DAG scheduling):
`src/paperbot/api/routes/agent_board.py:1294-1300`
```python
dag = TaskDAG(planning_tasks)
batches = dag.topological_batches()

yield StreamEvent(
    type="progress",
    data={
        "phase": "executing",
```

Example control flow excerpt (verification-repair loop):
`src/paperbot/repro/orchestrator.py:281-302`
```python
for repair_attempt in range(self.config.max_repair_loops + 1):
    self.progress.repair_loop_count = repair_attempt
    self._update_stage(PipelineStage.VERIFICATION)
    await self._run_verification()
    ...
    if error and repair_attempt < self.config.max_repair_loops:
        self._update_stage(PipelineStage.DEBUGGING)
        debug_result = await self._run_debugging()
```

## 4. Tools & External Integrations

- **Anthropic API (Claude commander/planner/reviewer):** task decomposition and output review in `src/paperbot/infrastructure/swarm/claude_commander.py:75-113` and `:241-289`.
- **OpenAI API (Codex worker loop):** coding agent dispatch and tool-calling loop in `src/paperbot/infrastructure/swarm/codex_dispatcher.py:206-227`, `:315-366`, `:678-727`.
- **VM/Sandbox tool layer:** LLM-callable tools (`read_file`, `write_file`, `run_command`, etc.) in `src/paperbot/infrastructure/swarm/sandbox_tool_executor.py:33-142`, executed against `SharedSandbox`.
- **Execution backends (Docker / E2B):** runtime selection for code execution in `src/paperbot/repro/repro_agent.py:149-190` and sandbox acquisition in `src/paperbot/api/routes/agent_board.py:201-225`.
- **Persistent session/task store (SQLAlchemy-backed pipeline sessions):** `PipelineSessionStore` wiring in `src/paperbot/api/routes/agent_board.py:47`, `:177-181`.
- **Event logging/bus for agent workflows:** unified event envelope and composite backends in `src/paperbot/api/main.py:106-119`, and event emission from orchestrators in `src/paperbot/repro/orchestrator.py:380-399`.
- **FastAPI SSE streaming interface:** agent progress and result streaming in endpoints like `src/paperbot/api/routes/gen_code.py:30-55` and `src/paperbot/api/routes/agent_board.py` (stream generators).

## 5. Notable Code Walkthrough

- `src/paperbot/api/routes/agent_board.py:25-46,1294-1490` - Main multi-agent board runtime: wires planner/executor/verification, builds DAG batches, executes parallel workers, handles pause/cancel, and streams SSE events.
- `src/paperbot/infrastructure/swarm/codex_dispatcher.py:315-520,678-876` - Core CodeAct-style loop: repeatedly invokes OpenAI tool-calling, executes tools, detects stagnation/repeats/errors, and determines completion/failure diagnostics.
- `src/paperbot/infrastructure/swarm/sandbox_tool_executor.py:33-142,168-277` - Defines the worker tool API and concrete VM-native implementations (file I/O, command execution, search, subtask updates, completion signal).
- `src/paperbot/repro/orchestrator.py:117-170,252-332` - Specialized Paper2Code orchestrator coordinating planning/coding/verification/debugging with retry loops and stage tracking.
- `src/paperbot/repro/repro_agent.py:89-137,254-349` - Entry agent deciding orchestrator-vs-legacy mode, initializing agents/backends, and invoking the multi-agent pipeline for `/api/gen-code`.

## 6. Use-Case Mapping

The assigned label **Code Generation** is partly correct but incomplete. The repository does generate code (especially through `ReproAgent` and Agent Board Codex workers), but the dominant runtime pattern is broader **workflow automation**: task decomposition, dependency scheduling, parallel dispatch, verification/repair loops, session persistence, and streaming lifecycle controls (`src/paperbot/api/routes/agent_board.py`, `src/paperbot/infrastructure/swarm/task_dag.py`, `src/paperbot/repro/orchestrator.py`). In other words, code generation is one stage inside a larger automated multi-agent pipeline. The better top-level category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Implements real runtime multi-agent coordination (not just role labels) with explicit planner/executor/reviewer separation.
  - Uses dependency-aware DAG batching for parallelizable tasks in production API paths.
  - Provides concrete tool-mediated agent execution in sandboxes with guardrails and progress telemetry.
  - Includes verification + iterative repair loops, giving measurable closure criteria beyond “LLM response.”
  - Exposes end-to-end streaming and persistence, making agent behavior observable for debugging/evaluation.

- **Limitations:**
  - Architecture is split across multiple paradigms (older coordinator + newer swarm/orchestrator), increasing conceptual and maintenance complexity.
  - Some “parallel” claims in Paper2Code are conservative/partial (e.g., `ParallelOrchestrator` currently delegates to sequential run).
  - Heavy dependence on external API keys/backends (Anthropic/OpenAI/E2B/Docker) can degrade behavior to fallback paths.
  - Large route modules (notably `agent_board.py`) centralize too much orchestration logic, reducing modular clarity.
  - Verification quality depends on command policies and sandbox environment; semantic correctness remains hard to guarantee.

- **Research relevance:**
  - Good evidence of manager-worker multi-agent software engineering workflows with explicit delegation and review loops.
  - Useful case study for tool-augmented LLM agents operating in persistent shared environments.
  - Demonstrates practical orchestration tradeoffs between DAG parallelism and sequential repair loops.
  - Offers instrumentation hooks (event envelopes, task logs, SSE traces) suitable for empirical MAS observability studies.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
