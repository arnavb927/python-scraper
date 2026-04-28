---
repo_name: deanpeters/Product-Manager-Skills
url: "https://github.com/deanpeters/Product-Manager-Skills"
stars: 3678
forks: 480
contributors_count: 3
last_commit_date: "2026-04-02T00:15:23+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T15:56:40.840666+00:00"
model: auto
duration_s: 71.2
clone_size_kb: 2871
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

This repository is primarily a **PM skill library plus execution harnesses**, not a standalone autonomous agent system. Users run either terminal scripts (for example `scripts/run-pm.sh` and `scripts/add-a-skill.sh`) or the Streamlit app at `app/main.py` to load `skills/*/SKILL.md`, inject those skill definitions into an LLM prompt, and generate PM artifacts/workflow outputs. The core problem it solves is making reusable product-management playbooks portable across agent surfaces (Claude, Codex, OpenAI/Ollama-backed chat). In practice, a user gets ranked skill selection, guided “interactive” sessions, or phase-by-phase workflow outputs, but each run is still one model call chain driven by prompt templates.

## 2. Agent Framework & Architecture

No runtime multi-agent framework (CrewAI/LangGraph/LangChain/AutoGen/LlamaIndex) is implemented in the executable code. The actual imports in app/runtime code are `anthropic`, `openai`, `streamlit`, `yaml`, and shell tooling (`app/main.py`, `scripts/*.sh`), while CrewAI appears only in documentation examples (`docs/Using PM Skills 101.md`, `docs/pm-skills-guide.jsx`), not in runtime orchestration.

Architecture is a **custom prompt-orchestration pattern**:
- `app/main.py` loads local markdown skills, parses frontmatter/sections, and builds a system prompt from the selected skill (`app/main.py:290-349`, `app/main.py:457-468`).
- Session handlers route by skill type (`component`, `interactive`, `workflow`) and repeatedly call a single provider client (`anthropic`, `openai`, or Ollama-compatible OpenAI endpoint) through one helper (`app/main.py:419-455`, `app/main.py:1515-1521`).
- CLI scripts provide wrapper automation: discovery, prompt generation, and optional handoff to `claude` or `codex` CLIs (`scripts/run-pm.sh:87-128`), plus a skill-authoring pipeline that delegates content generation to one adapter at a time (`scripts/add-a-skill.sh`, `scripts/adapters/*.sh`).

“Intelligence” lives mostly in markdown skill content and prompt scaffolding, not in planner/router agents.

## 3. Orchestration Pattern

Closest match: **sequential workflow automation (single-agent prompt pipeline)**, not hierarchical multi-agent orchestration.

Control flow in app sessions is a router over skill type, then serial model calls:

```1509:1521:app/main.py
system = build_system_prompt(skill)
scenario = st.session_state.get("scenario", "")

if skill["type"] == "component":
    render_component_session(skill, provider, api_key, model, system, scenario)
elif skill["type"] == "interactive":
    render_interactive_session(skill, provider, api_key, model, system, scenario)
elif skill["type"] == "workflow":
    render_workflow_session(skill, provider, api_key, model, system, scenario)
```

Workflow mode iterates phases in-order and calls the same model each phase:

```1719:1729:app/main.py
if run_all:
    with st.spinner(f"Running all {len(phases)} phases…"):
        try:
            for idx, phase_def in enumerate(phase_defs, start=1):
                prompt = build_phase_prompt(
                    scenario, phase_def["name"], phase_def["body"], idx, len(phases)
                )
                msgs = [{"role": "user", "content": prompt}]
                response = call_model(provider, api_key, model, system, msgs)
                workflow_outputs[phase_def["name"]] = response
```

So this is an orchestrated **single-LLM, multi-step pipeline**, not multiple coordinated runtime agents.

## 4. Tools & External Integrations

- **LLM provider APIs (Anthropic/OpenAI/Ollama-compatible)**: wired in `call_model()` and provider config helpers (`app/main.py:33-68`, `app/main.py:419-455`).
- **Terminal AI CLIs (`claude`, `codex`)**: invoked by `scripts/run-pm.sh` for direct execution (`scripts/run-pm.sh:114-128`).
- **Claude CLI adapter for skill generation**: `scripts/adapters/claude-code.sh` shells out to `claude --message ...` for analysis/plan/generation/docs updates (`scripts/adapters/claude-code.sh:52-60`, `:88-90`, `:129-137`).
- **Manual adapter (human-in-the-loop external AI)**: captures pasted responses and parses file blocks (`scripts/adapters/manual.sh:14-40`, `:119-155`).
- **Filesystem as knowledge base**: all skills loaded from local `skills/*/SKILL.md` (`app/main.py:290-349`), command markdown loaded by shell scripts (`scripts/run-pm.sh:87-103`).
- **Git integration (staging automation)**: `add-a-skill.sh` stages generated skills/docs (`scripts/add-a-skill.sh:432-453`).
- **No MCP/browser automation/vector DB/RAG index/database integration** found in runtime code.

## 5. Notable Code Walkthrough

- `app/main.py:290-349,419-455,1510-1737` - Main runtime engine: parses skill markdown, builds prompts, chooses provider/model, and executes component/interactive/workflow sessions through serial LLM calls.
- `scripts/run-pm.sh:87-134` - Lightweight terminal orchestration: maps a skill/command name to a file path prompt, then prints it or executes via `claude`/`codex`.
- `scripts/add-a-skill.sh:212-325,464-503` - End-to-end content-to-skill workflow (analyze -> plan -> generate -> validate -> install -> docs -> git stage) with user checkpoints.
- `scripts/adapters/claude-code.sh:21-61,92-144` - Adapter abstraction that turns pipeline steps into Claude CLI prompts and parses multi-file output blocks.
- `scripts/build-a-skill.sh:186-236,296-376` - Deterministic interactive wizard for creating compliant skills without autonomous agent planning.

## 6. Use-Case Mapping

Assigned label `Browser / Terminal Use` is **partly accurate** (there are explicit terminal flows via `scripts/run-pm.sh` and other shell utilities), but after reading code the stronger primary category is **Workflow Automation**. The system’s core behavior is automating PM workflow steps and skill-authoring pipelines using scripted orchestration and sequential LLM calls, rather than browser control or terminal-operation agents acting on arbitrary environments. There is no browser automation stack (Playwright/Browserbase) and no generalized terminal-execution agent loop.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong prompt modularity via standardized `SKILL.md` anatomy and frontmatter validation (`scripts/check-skill-metadata.py`).
  - Practical multi-surface integration (Streamlit UI + shell + Claude/Codex CLI handoff) with minimal dependencies.
  - Clear deterministic orchestration scripts for repeatable content distillation (`add-a-skill.sh`, `build-a-skill.sh`).
  - Supports multiple LLM backends including local Ollama-compatible mode (`app/main.py:442-452`).
  - Human oversight checkpoints in generation pipeline reduce blind autonomous edits.

- **Limitations:**
  - No true runtime multi-agent coordination; all execution is effectively single-agent sequential prompting.
  - “Workflow” decomposition is prompt-level phase splitting, not agent specialization with explicit inter-agent contracts.
  - No memory/store beyond Streamlit session state; no retrieval index or long-horizon state persistence.
  - Heavy dependence on markdown prompt quality; little programmatic output verification beyond metadata checks.
  - Some shell scripts mix UX and orchestration logic, limiting portability across OS/shell environments.

- **Research relevance:**
  - Good evidence for **agent-adjacent workflow engineering** where structured prompt assets are treated as reusable operational modules.
  - Useful example of **human-in-the-loop orchestration** with approval gates in AI-assisted artifact generation.
  - Illustrates distinction between “multi-step LLM pipelines” and true multi-agent systems in empirical taxonomy.
  - Relevant for studies on prompt-governance and reproducibility in domain-specific AI copilots.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
