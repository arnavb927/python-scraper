---
repo_name: s-smits/agentic-cursorrules
url: "https://github.com/s-smits/agentic-cursorrules"
stars: 649
forks: 57
contributors_count: 3
last_commit_date: "2025-11-19T02:08:44+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T16:09:05.661131+00:00"
model: auto
duration_s: 66.0
clone_size_kb: 186
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`agentic-cursorrules` is a Python CLI that prepares **domain-scoped instruction files** for use with AI coding assistants, rather than running LLM agents itself. A user runs commands like `agentic-cursorrules --init` or `--auto-config`, which scan a target repository, detect important directories, and build/refresh a YAML config (`main.py:43-176`, `agentic_cursorrules/smart_analyzer.py:105-125`). It then generates per-domain markdown agent files (for example `agent_backend_api.md`) containing a constrained file tree and boundary instructions (`main.py:288-291`, `agentic_cursorrules/agent_generator.py:73-83`). The practical output is workflow scaffolding that helps humans run multiple external agents safely by partitioning repository context.

## 2. Agent Framework & Architecture

No LLM-agent framework (LangGraph, LangChain, CrewAI, AutoGen, etc.) is used in code. The dependency set only includes `gitignore-parser`, `pyyaml`, and `rich` (`pyproject.toml:7-11`), and there are no imports of model SDKs or orchestration runtimes across source files.

Architecture is a custom CLI pipeline:
1. load/derive config (`main.py`, `config_updater.py`, `smart_analyzer.py`),
2. resolve focus directories and produce directory trees (`project_tree_generator.py`),
3. emit markdown “agent” prompt files (`agent_generator.py`).

The “intelligence” is heuristic and filesystem-based, not LLM-based: directory significance thresholds, extension matching, and fallback scanning logic drive decisions (`smart_analyzer.py:154-210`, `project_tree_generator.py:117-200`). So this repo implements **agent workflow preparation** (prompt/boundary generation), not runtime multi-agent reasoning.

## 3. Orchestration Pattern

Closest match: **sequential pipeline (other)**, not runtime MAS orchestration.

Control flow is linear in `main.py`: analyze/update config -> find focus dirs -> generate trees -> generate agent markdown files. There is optional recurring rerun every 60 seconds (`main.py:211-296`), but still as a repeated sequential batch process.

```243:291:main.py
            for focus_dir in found_dirs:
                ...
                tree_content = generator.generate_tree(
                    focus_dir, 
                    skip_dirs=skip_dirs,
                    config_paths=config_paths
                )
                ...
                with open(tree_files_dir / f'tree_{focus_dir.name}.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(tree_content))
                processed_dirs.add(rel_path)
            
            output_dir = config_dir if args.local_agents else project_dir
            generate_agent_files([str(d.relative_to(project_dir)) for d in found_dirs], config_dir, project_dir, output_dir)
```

```73:83:agentic_cursorrules/agent_generator.py
            agent_content = f"""You are an agent that specializes in {dir_description} of this project...
{tree_content}
...
"""
            output_path = project_dir / agent_name
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(agent_content)
```

## 4. Tools & External Integrations

- **Local filesystem scanning/walking**: directory traversal, code-file counting, and tree generation (`smart_analyzer.py:154-184`, `project_tree_generator.py:53-81`, `project_tree_generator.py:202-258`).
- **YAML config I/O**: reads/writes `config.yaml` and variants for pipeline state (`main.py:214-221`, `config_updater.py:131-137`, `smart_analyzer.py:223-249`).
- **`.gitignore` integration** via `gitignore-parser`: applies ignore semantics while rendering domain trees (`project_tree_generator.py:29-38`, `project_tree_generator.py:61-66`).
- **CLI/terminal UX** via Rich: spinners, prompts, panels, and tree visualization (`main.py:8-12`, `main.py:92-95`, `project_tree_generator.py:83-115`).
- **No external model/API/tool servers**: no OpenAI/Anthropic APIs, MCP clients, browser automation, vector DBs, SQL backends, or HTTP integrations observed.

## 5. Notable Code Walkthrough

- `main.py:43-305` - Central orchestrator CLI. Parses modes (`--init`, `--auto-config`, `--tree-input`, `--recurring`), runs analyzer/tree generation, and triggers agent-file output.
- `agentic_cursorrules/smart_analyzer.py:85-252` - Heuristic project analyzer. Detects likely domain directories from known patterns and code-density counts, then updates config.
- `agentic_cursorrules/project_tree_generator.py:10-200` - Builds ASCII and Rich trees for each selected domain while honoring `.gitignore`, exclude lists, and nested focus-path handling.
- `agentic_cursorrules/agent_generator.py:5-91` - Emits per-domain markdown prompts that constrain future assistant actions to a specific directory subtree.
- `agentic_cursorrules/config_updater.py:29-150` - Converts pasted tree text into structured config (focus dirs + exclusions) and persists deterministic YAML ordering.

## 6. Use-Case Mapping

This repo fits **Workflow Automation**: it automates repetitive setup work needed to run multi-agent coding workflows in tools like Cursor by generating scoped, reusable rule files from project structure. Concretely, it turns a repo’s tree into domain-specific instruction artifacts that reduce cross-domain edits and coordination overhead (`main.py:227-291`, `agent_generator.py:73-83`).  

However, it does **not** implement multi-agent runtime logic itself; instead it prepares constraints for external agents/users to apply during conversations.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Practical guardrail generation from real filesystem structure, including `.gitignore` awareness.
  - Multiple config acquisition paths (`--init`, auto scan, pasted tree) lower onboarding friction.
  - Deterministic, human-readable outputs (YAML + markdown trees) are easy to audit and version.
  - Clear boundary-oriented prompt templates directly target agent scope creep.

- **Limitations:**
  - No built-in LLM runtime, planner, or inter-agent protocol; “agentic” behavior is externalized.
  - Heuristic directory detection may misclassify unusual monorepos or deep custom layouts.
  - Potential filename collisions/ambiguity in generated agent names for similarly named directories.
  - No embedded evaluation loop to validate that downstream agents actually obey generated boundaries.

- **Research relevance:**
  - Evidence of a **prompt-scaffolding approach** to multi-agent coordination via context partitioning.
  - Useful artifact for studying **static boundary constraints** as an alternative to runtime routing.
  - Example of lightweight, non-LLM orchestration support tooling in agentic developer workflows.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
