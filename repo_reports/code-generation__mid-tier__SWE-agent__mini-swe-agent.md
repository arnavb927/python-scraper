---
repo_name: SWE-agent/mini-swe-agent
url: "https://github.com/SWE-agent/mini-swe-agent"
stars: 3960
forks: 549
contributors_count: 31
last_commit_date: "2026-04-17T04:30:22+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, Browser / Terminal Use]
generated_at: "2026-04-27T12:26:14.567225+00:00"
model: auto
duration_s: 80.4
clone_size_kb: 2223
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`mini-swe-agent` is a compact CLI-first coding agent that takes a natural-language software task, calls an LLM, executes model-produced shell commands, and iterates until it emits a final submission. A typical user runs `mini` (from `src/minisweagent/run/mini.py`) with a task and model, and gets an interactive terminal loop plus a saved trajectory JSON. The core value is lightweight issue-solving automation for local repos and SWE-bench-style tasks without a large orchestration stack. It also provides benchmark runners (notably SWE-bench batch execution) and multiple runtime environments (local, Docker, Singularity, etc.) for reproducible execution.

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework**, not LangGraph/LangChain/AutoGen/CrewAI. Evidence: internal protocol interfaces and factory loaders in `src/minisweagent/__init__.py:43-81`, `src/minisweagent/agents/__init__.py:8-29`, `src/minisweagent/models/__init__.py:45-114`, and direct model API wrappers (e.g., LiteLLM) in `src/minisweagent/models/litellm_model.py:48-148`.

Architecture is a polymorphic 3-part loop: **Agent + Model + Environment**. `DefaultAgent` owns the control loop and message history (`src/minisweagent/agents/default.py:33-123`), `Model` adapters convert chat responses into executable actions (`src/minisweagent/models/litellm_model.py:80-134`), and `Environment` implementations execute commands (`src/minisweagent/environments/local.py:23-53` plus containerized variants). Intelligence primarily lives in prompt templates/config and in model outputs interpreted as tool calls.

There are two runtime agent classes (`default`, `interactive`), but they are alternative modes of a single active agent instance per task, not multiple cooperating role-specialized agents. `InteractiveAgent` adds human-in-the-loop confirmation/override modes (`src/minisweagent/agents/interactive.py:23-183`).

## 3. Orchestration Pattern

Closest pattern: **sequential single-agent loop** (with optional human interrupt/approval), plus independent parallelization across benchmark instances.

Control flow inside one run is linear: initialize messages -> query model -> execute actions -> append observations -> repeat until exit (`src/minisweagent/agents/default.py:77-123`).

Excerpt (`src/minisweagent/agents/default.py:85-102`):
```python
while True:
    try:
        self.step()
    ...
    if self.messages[-1].get("role") == "exit":
        break

def step(self) -> list[dict]:
    return self.execute_actions(self.query())
```

Tool-call-to-execution path is explicit: model response is parsed into `actions`, then each action is executed by environment (`src/minisweagent/models/litellm_model.py:87-119`, `src/minisweagent/agents/default.py:119-123`).

Excerpt (`src/minisweagent/agents/default.py:119-123`):
```python
def execute_actions(self, message: dict) -> list[dict]:
    outputs = [self.env.execute(action) for action in message.get("extra", {}).get("actions", [])]
    return self.add_messages(*self.model.format_observation_messages(message, outputs, self.get_template_vars()))
```

## 4. Tools & External Integrations

- **Shell/terminal execution**: primary tool is a `bash` function-call schema (`src/minisweagent/models/utils/actions_toolcall.py:11-27`), executed locally via `subprocess.run(..., shell=True)` in `src/minisweagent/environments/local.py:23-40`.
- **LLM gateways/APIs**: LiteLLM backend (`litellm.completion`) in `src/minisweagent/models/litellm_model.py:63-70`; additional adapters for OpenRouter/Portkey/Requesty via model factory mapping in `src/minisweagent/models/__init__.py:78-89`.
- **Containerized execution environments**: Docker/Singularity/SWE-ReX/Bubblewrap/Contree selectable via environment mapping in `src/minisweagent/environments/__init__.py:8-16`; SWE-bench image wiring in `src/minisweagent/run/benchmarks/swebench.py:93-108`.
- **Dataset/service integration**: Hugging Face `datasets.load_dataset` for SWE-bench subsets in `src/minisweagent/run/benchmarks/swebench.py:236-241`.
- **CLI framework and config system**: Typer command interfaces in `src/minisweagent/run/mini.py:50-66` and `src/minisweagent/run/benchmarks/swebench.py:214-229`; Jinja2 template rendering for prompts and observations in `src/minisweagent/agents/default.py:55-56` and `src/minisweagent/models/utils/actions_toolcall.py:82-84`.
- **Not present**: no browser automation stack, vector DB/RAG pipeline, or MCP server orchestration in core runtime.

## 5. Notable Code Walkthrough

- `src/minisweagent/agents/default.py:33-155` - Core runtime loop. It manages prompt initialization, model querying, action execution, stopping conditions (step/cost), and trajectory serialization; this is the heart of agent behavior.
- `src/minisweagent/agents/interactive.py:23-183` - Human-in-the-loop extension with `human/confirm/yolo` modes, slash commands, and command approval gates; important for practical safe usage on real repos.
- `src/minisweagent/models/litellm_model.py:48-148` - Main model adapter. It calls LiteLLM, injects the bash tool schema, parses tool calls into actions, tracks cost, and formats tool outputs back into chat messages.
- `src/minisweagent/models/utils/actions_toolcall.py:11-103` - Defines the only first-class tool (`bash`), validates/decodes function-call arguments, and converts environment outputs into observation messages.
- `src/minisweagent/run/benchmarks/swebench.py:136-279` - Batch orchestrator for SWE-bench. It spins per-instance runs in a thread pool and records per-instance outputs; this is where scalability/benchmark automation happens.

## 6. Use-Case Mapping

This repository strongly realizes **Code Generation** as assigned: the agent iteratively edits codebases by issuing shell commands, running tests, and eventually returning a patch/submission string (`src/minisweagent/environments/local.py:55-66`, `src/minisweagent/agents/default.py:77-123`). The SWE-bench runners operationalize this directly on software issue-fixing tasks (`src/minisweagent/run/benchmarks/swebench.py:136-191`). 

That said, the mechanism is also clearly **Browser / Terminal Use**-adjacent (terminal-heavy tool execution), but not browser-centric. If forced to pick one best label from behavior, `Code Generation` remains the best fit for the main workflow.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Very clear minimal control loop with low abstraction overhead (`DefaultAgent`), making behavior easy to audit.
- Strong modularity via protocol-based Agent/Model/Environment separation and runtime class selection.
- Practical safety layer through interactive confirmation and mode switching in `InteractiveAgent`.
- Benchmark-oriented engineering (SWE-bench batch runner, progress tracking, trajectory persistence).
- Tool-call handling is explicit and deterministic (strict parsing + formatted observations).

- **Limitations:**
- Single-tool design (`bash`) constrains richer agent capabilities (no native web/API/file semantic tools).
- No true multi-agent coordination (planner-worker/debate/swarm) within a task; only one active LLM agent loop.
- Local execution uses `shell=True`, which increases command-safety risk if prompts are adversarial.
- Error recovery relies heavily on exception flow; limited structured retry/replanning at the agent policy level.
- Context strategy is mostly full message history; no long-horizon memory/RAG subsystem for large tasks.

- **Research relevance:**
- Useful as a reference implementation of a minimal tool-using coding agent architecture.
- Good evidence for how much SWE-bench performance can be achieved with simple sequential loops.
- Illustrates trade-offs between simplicity and safety/control in terminal-executing LLM agents.
- Supports studies on human-in-the-loop command approval effects in agentic coding workflows.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
