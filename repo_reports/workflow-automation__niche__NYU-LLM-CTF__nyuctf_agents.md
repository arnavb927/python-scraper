---
repo_name: NYU-LLM-CTF/nyuctf_agents
url: "https://github.com/NYU-LLM-CTF/nyuctf_agents"
stars: 142
forks: 33
contributors_count: 10
last_commit_date: "2025-10-25T20:57:58+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 1
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T18:04:30.560415+00:00"
model: auto
duration_s: 81.5
clone_size_kb: 494
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`nyuctf_agents` is a CTF-solving automation framework that runs LLM agents against benchmarked NYU CTF tasks inside Dockerized challenge environments. A user typically runs `run_dcipher.py` (multi-agent), `run_single_executor.py` (ablation), or `run_baseline.py` (single-agent baseline), specifying dataset split and challenge name. The system boots an environment container, copies challenge files in, and lets agents iteratively call tools like shell execution, reverse-engineering helpers, and file creation until they submit a flag or give up. Outputs are structured logs containing full conversations, costs, and success/failure metadata (`run_dcipher.py:17-120`, `nyuctf_multiagent/agent.py:451-474`).

## 2. Agent Framework & Architecture

This repo uses a **custom multi-agent framework**, not LangGraph/CrewAI/AutoGen/LlamaIndex. The orchestration and agent classes are hand-implemented in `nyuctf_multiagent/agent.py`, with custom tool abstractions in `nyuctf_multiagent/tools/tool.py`, custom conversation state in `nyuctf_multiagent/conversation.py`, and backend adapters for OpenAI/Anthropic/Gemini/Together (`nyuctf_multiagent/backends/__init__.py:1-8`).

The main D-CIPHER architecture has three roles: **AutoPrompter** (optional), **Planner**, and **Executor**. At startup, `run_dcipher.py` instantiates one backend per role with role-specific prompt YAML and toolsets from config, then runs `PlannerExecutorSystem.run()` (`run_dcipher.py:90-119`, `configs/dcipher/base_planner_executor.yaml:5-39`). “Intelligence” is distributed across (a) role prompts loaded by `PromptManager`, (b) model function-calling decisions, and (c) explicit control logic in `PlannerExecutorSystem` for delegation loops (`nyuctf_multiagent/prompting.py:3-25`, `nyuctf_multiagent/agent.py:502-563`).

The baseline path (`run_baseline.py`) is separate and primarily single-agent, but the repo’s flagship D-CIPHER path is runtime multi-agent with coordinated planner/executor interactions.

## 3. Orchestration Pattern

Closest pattern: **hierarchical (manager-worker)** with iterative delegation.

The planner acts as manager and issues `delegate(task=...)`; the system then spins up a fresh executor worker, gathers its summary, and feeds that back to the planner as an observation:

```525:531:nyuctf_multiagent/agent.py
if self.planner.delegated_task is not None:
    result = self.run_executor(self.planner.delegated_task)
    tool_result = ToolResult(name=DelegateTool.NAME, id=self.planner.delegated_task.id, result=result)
    self.planner.add_observation_message(tool_result)
    self.planner.delegated_task = None
```

Worker lifecycle is isolated per delegated task (`executor = self.executor.new()`), then terminated by `finish_task` summary or error/round limits:

```532:556:nyuctf_multiagent/agent.py
def run_executor(self, task):
    executor = self.executor.new()
    ...
    while not self.environment.solved and not executor.finished ...
        executor.run_one_round()
    ...
    if executor.finished and executor.finish_summary is not None:
        return executor.finish_summary
```

This is not a graph-state-machine framework; transitions are hard-coded loop-and-branch logic in Python.

## 4. Tools & External Integrations

- **Docker runtime environment**: The environment container is launched/stopped via `docker run/stop`, and challenge files are copied with `docker cp` (`nyuctf_multiagent/environment.py:44-70`, `:33-37`).
- **Shell/terminal execution in container**: `run_command` executes arbitrary bash commands inside the environment container with timeout handling (`nyuctf_multiagent/tools/run_command.py:6-50`).
- **Reverse-engineering tooling via Ghidra scripts**: `disassemble` and `decompile` tools call `/opt/ghidra/customScripts/*.sh` inside Docker and parse JSON results (`nyuctf_multiagent/tools/reversing.py:9-53`, `:58-124`).
- **Filesystem write tool**: `create_file` writes model-generated content to temp host file then copies into container path (`nyuctf_multiagent/tools/editing.py:22-29`).
- **LLM API providers**: OpenAI, Anthropic, Gemini, Together backends with function/tool calling schemas and cost accounting (`nyuctf_multiagent/backends/openai_backend.py:61-93`, `anthropic_backend.py:40-69`, `gemini_backend.py:45-74`, `backends/__init__.py:1-8`).
- **CTF dataset/challenge package**: Uses `nyuctf` dataset/challenge classes to load tasks and flags (`run_dcipher.py:6-8`, `run_single_executor.py:6-8`).

No MCP server, vector DB, browser automation, or RAG pipeline is wired in this codebase.

## 5. Notable Code Walkthrough

- `nyuctf_multiagent/agent.py:409-563` — Core multi-agent engine (`PlannerExecutorSystem`) implementing planner loop, delegation trigger, executor spawning, result return, and cost/termination guards.
- `run_dcipher.py:90-119` — Composition root that binds config → role backends → prompts → agents, then launches the full planner/executor run.
- `nyuctf_multiagent/environment.py:9-75` — Execution substrate managing Docker lifecycle, challenge file staging, and tool dispatch.
- `nyuctf_multiagent/tools/misc.py:57-118` — Inter-agent protocol tools (`delegate`, `finish_task`, `generate_prompt`) that encode planner-worker communication contracts.
- `configs/dcipher/base_planner_executor.yaml:5-39` — Declares role-specific models, max rounds, and crucially distinct planner vs executor toolsets (evidence of explicit role separation).

## 6. Use-Case Mapping

The assigned category **Workflow Automation** fits well. The repo automates a repeated workflow: initialize challenge environment, reason over task state, execute command/tool actions, delegate subtasks to worker agents, aggregate results, and stop on success/cost/round constraints. This is a structured automated pipeline rather than open-ended chat, with clear control-flow stages and machine-readable logs (`nyuctf_multiagent/agent.py:502-563`, `environment.py:29-42`, `run_dcipher.py:118-119`).

It also has strong “terminal use” characteristics, but the dominant design is end-to-end orchestration of a complex task workflow, so `Workflow Automation` remains the best label.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear runtime multi-agent coordination (planner→executor) with explicit delegation contracts (`delegate`, `finish_task`).
  - Role-specific tool access and prompts improve separation of concerns (`configs/dcipher/base_planner_executor.yaml:12-39`).
  - Backend-agnostic provider abstraction across major LLM APIs with shared tool-calling interface.
  - Practical execution substrate (Docker + shell + reversing tools) enables grounded action, not just text reasoning.
  - Detailed experiment logging (conversation traces, costs, errors) supports reproducibility and analysis.

- **Limitations:**
  - Orchestration is rigid and hand-coded; no adaptive routing, dynamic team composition, or richer graph control.
  - Tool safety/sandbox policy is minimal beyond Docker; arbitrary shell command execution is powerful but risky.
  - Limited memory strategy (truncating older observations) may drop useful long-horizon context (`conversation.py:55-70`).
  - Error handling is mostly local and fallback-based; no robust retry/backoff policy across all backends/tools.
  - No integrated retrieval/memory store or external knowledge system; performance depends heavily on prompt/model/tool use.

- **Research relevance:**
  - Good evidence of **hierarchical MAS** behavior in practical LLM-agent systems.
  - Useful case study of **tool-augmented agent teamwork** under constrained budgets and rounds.
  - Supports study of **role specialization** effects via planner/executor/autoprompter prompt and tool separation.
  - Provides logged trajectories suitable for evaluating delegation quality, failure modes, and cost-performance tradeoffs.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
