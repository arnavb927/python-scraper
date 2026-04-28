---
repo_name: ChicagoHAI/NeuriCo
url: "https://github.com/ChicagoHAI/NeuriCo"
stars: 118
forks: 19
contributors_count: 5
last_commit_date: "2026-04-13T22:12:41+00:00"
primary_use_case: Simulation
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T16:58:55.117104+00:00"
model: auto
duration_s: 120.3
clone_size_kb: 24205
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

NeuriCo is an automated research-execution system: a user submits an idea spec (YAML), then runs the CLI pipeline to gather literature/resources, run experiments via an LLM coding agent, and optionally draft a paper. In practice, the entrypoint is `src/core/runner.py` (also exposed through the `neurico` wrapper script), which sets up a workspace/GitHub repo and drives staged execution. The output is a populated research workspace with logs, scripts/results, documentation (`REPORT.md`, `README.md`), and optionally a LaTeX paper draft. It is less a chat assistant and more an end-to-end workflow runner for “research project automation.”

## 2. Agent Framework & Architecture

This repo does **not** use CrewAI/LangGraph/AutoGen as the main orchestrator. The primary runtime is a **custom Python orchestrator** that shells out to external agent CLIs (`claude -p`, `codex exec`, `gemini`) via `subprocess.Popen` (`src/core/runner.py:44-50`, `src/agents/resource_finder.py:27-43`, `src/core/pipeline_orchestrator.py:416-426`).

High-level architecture in the main NeuriCo path is stage-based:
1) Resource Finder agent,  
2) optional human checkpoint,  
3) Experiment Runner agent,  
4) optional Paper Writer agent (`src/core/pipeline_orchestrator.py:172-236`, `src/core/runner.py:306-390`).  
Each “agent” is effectively a separate prompted CLI session, with prompts generated from templates (`src/templates/prompt_generator.py:112-200`, `:624-772`) and tracked using pipeline state files (`.neurico/pipeline_state.json`).

There is also a bundled `services/paper-finder` subsystem that is a separate multi-component agent service. That service uses a custom “operative” pattern and imports `langchain_core` callbacks in API routes (`services/paper-finder/agents/mabool/api/mabool/api/round_v2_routes.py:11-15`), but this is auxiliary to NeuriCo’s main orchestration and is called indirectly (via helper script hitting localhost API).

## 3. Orchestration Pattern

Closest match: **sequential workflow automation (pipeline)** with optional checkpoint, not a graph/swam. Control is centralized in one orchestrator that invokes stage agents in order and persists state.

```172:181:src/core/pipeline_orchestrator.py
# STAGE 1: Resource Finder
if not skip_resource_finder:
    results['stages']['resource_finder'] = self._run_resource_finder(
        idea=idea,
        provider=provider,
        timeout=resource_finder_timeout,
        full_permissions=full_permissions
    )
```

```203:210:src/core/pipeline_orchestrator.py
# STAGE 3: Experiment Runner
results['stages']['experiment_runner'] = self._run_experiment_runner(
    idea=idea,
    provider=provider,
    timeout=experiment_runner_timeout,
    full_permissions=full_permissions,
    use_scribe=use_scribe
)
```

Each stage then launches one external LLM coding agent process using provider-specific CLI commands (`src/agents/resource_finder.py:126-142`, `src/core/pipeline_orchestrator.py:366-389`, `src/agents/paper_writer.py:250-267`).

## 4. Tools & External Integrations

- **LLM coding CLIs (Claude/Codex/Gemini)**: main execution engine for resource-finding, experimenting, and paper-writing (`src/agents/resource_finder.py:30-43`, `src/core/pipeline_orchestrator.py:366-444`, `src/agents/paper_writer.py:22-26`).
- **GitHub + git automation**: repo creation/clone/commit/push through PyGithub + GitPython (`src/core/github_manager.py:20-33`, `:118-212`; wired from `src/core/runner.py:182-273`, `:807-837`).
- **Prompt templating (Jinja2)**: core “intelligence scaffolding” for agent behavior/instructions (`src/templates/prompt_generator.py:45-56`, `:112-200`, `:524-586`).
- **Paper Finder HTTP API service**: helper script calls `http://localhost:8000/api/2/rounds` via `httpx` (`templates/skills/paper-finder/scripts/find_papers.py:21-37`), with service endpoint implemented in FastAPI (`services/paper-finder/agents/mabool/api/mabool/api/round_v2_routes.py:30-75`).
- **Academic/data sources via agent actions in prompt policy**: instructions explicitly direct arXiv, Semantic Scholar, Papers with Code, HuggingFace datasets, Kaggle, GitHub cloning (`templates/agents/resource_finder.txt:234-377`, `:587-609`).
- **Filesystem + local process tooling**: agents are instructed to create environments, install deps (`uv`), download files, and produce structured workspace outputs (`templates/agents/resource_finder.txt:54-104`, `templates/agents/session_instructions.txt:8-75`).

## 5. Notable Code Walkthrough

- `src/core/runner.py:111-390` - Main runtime entrypoint that resolves idea/workspace/GitHub context and chooses multi-agent pipeline vs legacy monolithic mode; this is where NeuriCo’s top-level control logic lives.
- `src/core/pipeline_orchestrator.py:100-236` - Canonical pipeline controller implementing stage order, failure handling, optional human approval, and persisted state/results for resumeability.
- `src/agents/resource_finder.py:67-270` - Executes the first agent session, logs transcripts, checks completion marker, and validates expected artifacts (`literature_review.md`, `resources.md`, papers/datasets/code dirs).
- `src/templates/prompt_generator.py:624-772` - Builds role/task prompts (resource-finder, comment-mode, paper-writer) from templates plus idea metadata; key location for behavioral constraints and policy injection.
- `services/paper-finder/agents/mabool/api/mabool/agents/paper_finder/paper_finder_agent.py:99-289` - Separate, richer multi-agent router (query analysis → route to specialized search operatives) used by the optional paper-finder service.

## 6. Use-Case Mapping

The assigned label **Simulation** does not match the main implementation. The code is fundamentally an **automated research workflow orchestrator**: it coordinates staged tasks (resource gathering, implementation/experiments, reporting, paper drafting), integrates GitHub/dev tooling, and executes operational pipelines over real files/repos/APIs (`src/core/pipeline_orchestrator.py`, `src/core/runner.py`, `templates/agents/session_instructions.txt`).  
A better category is **Workflow Automation**. It does involve agentic behavior, but not simulation of environments/agents as the core product output.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear staged orchestration with resumable state and explicit handoff artifacts (`pipeline_state.json`, `pipeline_results.json`).
  - Provider-agnostic agent execution (Claude/Codex/Gemini) with unified transcript logging.
  - Strong prompt-engineered operational safeguards (workspace checks, environment isolation, deliverable checklists).
  - Practical DevOps integration (workspace bootstrapping, GitHub repo lifecycle, commit/push automation).
  - Includes an optional specialized retrieval service (`paper-finder`) with internal agent routing logic.

- **Limitations:**
  - “Multi-agent” in main path is mostly sequential single-agent sessions per stage, not concurrent collaboration.
  - Heavy reliance on long static prompt templates; limited learned/pluggable planning logic in code.
  - Many integrations are instruction-level (agent is told to use tools) rather than strongly typed tool APIs enforced in orchestrator.
  - Robustness depends on external CLIs and environment setup; failures can be operationally brittle.
  - Paper-finder service is noted as snapshot/not actively maintained (`services/paper-finder/README.md`).

- **Research relevance:**
  - Good example of **LLM-agent workflow orchestration** where control logic is in deterministic Python and cognition is delegated to prompted agent sessions.
  - Useful evidence for studying **prompt-as-policy** in autonomous coding/research pipelines.
  - Demonstrates hybrid architecture: lightweight orchestrator + external tool-using agents + optional specialist retrieval microservice.
  - Illustrates pragmatic MAS-lite design tradeoffs vs fully graph-based/runtime tool-call planners.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
