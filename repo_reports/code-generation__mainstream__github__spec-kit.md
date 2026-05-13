---
repo_name: github/spec-kit
url: "https://github.com/github/spec-kit"
stars: 90307
forks: 7779
contributors_count: 176
last_commit_date: "2026-04-22T21:44:06+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:15:26.321276+00:00"
model: auto
duration_s: 74.4
clone_size_kb: 7900
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`spec-kit` is a Python CLI toolkit (`specify`) that bootstraps and runs Spec-Driven Development workflows by installing command templates, agent integrations, and optional reusable workflows into a project. In practice, users run commands like `specify init ...` to scaffold `.specify/` assets plus integration-specific command/skill files, then run workflow steps that dispatch prompts/commands through external coding-agent CLIs. The repo’s core value is not an in-process LLM runtime, but a standardized orchestration layer that lets different agent tools (Claude, Codex, Gemini, etc.) execute the same SDD lifecycle (`specify -> plan -> tasks -> implement`). It also includes resumable workflow execution with step state, control-flow primitives, and integration-specific formatting/dispatch logic.

## 2. Agent Framework & Architecture

This repo uses a **custom framework**, not LangChain/LangGraph/CrewAI/AutoGen/LlamaIndex. The dependency list (`typer`, `click`, `rich`, `pyyaml`, etc.) contains no major LLM orchestration framework imports (`pyproject.toml:6-16`), and agent execution is implemented directly via subprocess dispatch methods (`src/specify_cli/integrations/base.py:160-238`).

Architecture-wise, the system has two layers:

1. **Integration layer**: A registry of integration adapters (`INTEGRATION_REGISTRY`) for many agent CLIs (`src/specify_cli/integrations/__init__.py:14-112`). Each adapter defines command-file layout plus how to invoke that agent CLI (`build_exec_args`, `dispatch_command`) (`src/specify_cli/integrations/base.py:122-238`, `830-1495`).
2. **Workflow runtime layer**: A YAML-driven workflow engine with typed steps (`command`, `prompt`, `shell`, `if`, `switch`, `while`, `fan-out`, `fan-in`, `gate`) (`src/specify_cli/workflows/__init__.py:19-68`, `src/specify_cli/workflows/engine.py:328-702`). “Intelligence” mostly lives in external agent CLIs + prompt templates; this repo provides orchestration, state, templating, and control flow.

So the repo is agentic infrastructure/orchestration rather than a single in-process model agent.

## 3. Orchestration Pattern

Closest match: **graph-style workflow state machine (custom), with sequential default execution plus branching/loop/fan-out nodes**.

Control flow is centrally orchestrated by `WorkflowEngine._execute_steps`, which iterates steps, dispatches by `type`, records state, and recursively runs nested `next_steps` (`src/specify_cli/workflows/engine.py:514-702`). It also has explicit handling for loop re-evaluation and fan-out item expansion, which is graph-like rather than simple linear scripting.

Example dispatch/registry flow:
- Step types are registered globally (`src/specify_cli/workflows/__init__.py:23-68`).
- Engine resolves each step by `step_type` and executes corresponding implementation (`src/specify_cli/workflows/engine.py:543-557`).

Example agent-command flow:
- `CommandStep` resolves integration/model/args and calls integration dispatch (`src/specify_cli/workflows/steps/command/__init__.py:31-84`).
- Integration dispatch builds slash command and executes external CLI via subprocess (`src/specify_cli/integrations/base.py:170-238`).

## 4. Tools & External Integrations

- **External coding-agent CLIs (Claude, Codex, Gemini, etc.)**: wired via integration registry and per-integration `build_exec_args`/`dispatch_command` (`src/specify_cli/integrations/__init__.py:40-112`, `src/specify_cli/integrations/base.py:122-238`).
- **Local shell/terminal execution**: `shell` workflow step runs arbitrary commands with `subprocess.run(..., shell=True)` (`src/specify_cli/workflows/steps/shell/__init__.py:20-67`).
- **Filesystem/project scaffolding**: command templates and skill files are written into agent-specific directories; context files are updated in-place (`src/specify_cli/agents.py:426-597`, `src/specify_cli/integrations/base.py:483-623`, `736-823`).
- **Workflow persistence store (local JSON files)**: run state/logs saved under `.specify/workflows/runs/<run_id>` (`src/specify_cli/workflows/engine.py:231-323`).
- **Git executable checks/init**: CLI uses subprocess checks for tools and can initialize git (`src/specify_cli/__init__.py` around `check_tool`/`subprocess.run` usage at ~417-489 from search hits).
- **No direct web search/RAG/vector DB/browser automation/MCP runtime** in core workflow execution code.

## 5. Notable Code Walkthrough

- `src/specify_cli/workflows/engine.py:328-702`  
  Core runtime orchestrator: loads/validates workflows, executes step graph, handles pause/resume/failure, nested control-flow recursion, and fan-out aggregation. This is the heart of runtime agent orchestration.

- `src/specify_cli/workflows/steps/command/__init__.py:13-147`  
  Bridge from abstract workflow steps to real agent execution: resolves templated inputs and dispatches Spec Kit slash commands through chosen integration CLIs.

- `src/specify_cli/integrations/base.py:56-238`  
  Defines integration abstraction and generic CLI dispatch path; this is where “agent tool adapters” are standardized.

- `src/specify_cli/integrations/__init__.py:40-112`  
  Registers the built-in integration catalog (many agent ecosystems), making the registry the source of available agent backends.

- `src/specify_cli/agents.py:426-597`  
  Command registration pipeline that transforms templates/frontmatter/placeholders into per-agent command files (Markdown/TOML/YAML/SKILL layouts), enabling the same workflows across different agent tools.

## 6. Use-Case Mapping

The assigned primary use case (`Code Generation`) is **partly correct but not the best top-level fit**. The code primarily implements a **workflow automation platform for agent-driven development tasks**: it scaffolds command packs, dispatches external agent CLIs across structured steps, and coordinates review/approval/control-flow gates (`workflows/speckit/workflow.yml:28-64`, `src/specify_cli/workflows/engine.py:380-452`). Code generation is an important downstream outcome (through `specify/plan/tasks/implement` commands), but the repository itself is more about orchestrating and standardizing those processes across agent backends. Best category: **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong adapter architecture for many agent ecosystems via consistent integration base classes (`src/specify_cli/integrations/base.py`).
  - Custom resumable workflow engine with explicit control-flow primitives and persisted state (`src/specify_cli/workflows/engine.py`).
  - Clear separation of concerns: template packaging, integration setup, and runtime execution are decoupled.
  - Practical interoperability layer: same SDD command set emitted in Markdown/TOML/YAML/skills formats (`src/specify_cli/agents.py`).
  - Extensibility through registries (`INTEGRATION_REGISTRY`, `STEP_REGISTRY`) for new agent backends and new step types.

- **Limitations:**
  - No in-process multi-agent reasoning/planning protocol; intelligence is delegated to external CLIs.
  - Limited output capture in command/prompt steps (comments note full stdout/stderr capture is planned) (`src/specify_cli/workflows/steps/command/__init__.py:23-27`, `src/specify_cli/workflows/steps/prompt/__init__.py:24-27`).
  - Security risk surface in `shell` step (`shell=True`) depends heavily on workflow trust (`src/specify_cli/workflows/steps/shell/__init__.py:28-35`).
  - Requirements in workflow definitions are declared but not fully enforced at runtime (`src/specify_cli/workflows/engine.py:50-52`).
  - Coordination semantics are mostly centralized orchestration, not autonomous peer-agent collaboration.

- **Research relevance:**
  - Useful evidence of **agent-tool interoperability design** across heterogeneous CLI agents.
  - Example of a **pragmatic orchestration layer** where agent steps are treated as pluggable external executors.
  - Demonstrates **stateful, resumable agent workflows** with branching/loop/fan-out primitives in production-style tooling.
  - Relevant for studying the boundary between “multi-agent systems” and “single orchestrator + multiple agent backends.”

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
