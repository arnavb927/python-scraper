---
repo_name: divar-ir/ai-doc-gen
url: "https://github.com/divar-ir/ai-doc-gen"
stars: 710
forks: 72
contributors_count: 3
last_commit_date: "2025-11-24T19:51:35+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T16:05:01.723266+00:00"
model: auto
duration_s: 70.8
clone_size_kb: 774
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`ai-doc-gen` is a Python CLI that automates repository analysis and documentation generation using LLM agents. A user runs commands like `analyze`, `generate readme`, or `generate ai-rules` (wired in `src/main.py:41-103`, `src/main.py:160-255`), and the tool produces `.ai/docs/*.md` analysis artifacts plus top-level docs such as `README.md`, `CLAUDE.md`, and `AGENTS.md`. It is also designed for scheduled batch automation via a GitLab cronjob flow that clones projects, runs analysis, commits outputs, and opens merge requests (`src/handlers/cronjob.py:53-204`). The core problem it solves is reducing manual architecture/documentation effort for onboarding and maintenance across many repos.

## 2. Agent Framework & Architecture

The runtime framework is **PydanticAI** (not CrewAI): imports and construction are explicit via `from pydantic_ai import Agent` and `Tool` (`src/agents/analyzer.py:8`, `src/agents/documenter.py:8`, `src/agents/ai_rules_generator.py:8`, `src/agents/tools/file_tool/file_reader.py:4`, `src/agents/tools/dir_tool/list_files.py:7`). Models are instantiated through PydanticAI’s OpenAI-compatible adapter (`OpenAIChatModel`, `OpenAIProvider`) in all agent modules (`src/agents/analyzer.py:10-13,194-210`; `src/agents/documenter.py:10-13,132-148`; `src/agents/ai_rules_generator.py:10-13,279-317`).

Architecture is a handler-agent CLI pipeline: command handlers create agent configs and invoke agent execution (`src/handlers/analyze.py:14-38`, `src/handlers/readme.py:14-33`, `src/handlers/ai_rules.py:14-40`). The main multi-agent component is `AnalyzerAgent`, which conditionally spins up **five specialized agents** (structure, dependencies, data flow, request flow, API) and runs them concurrently (`src/agents/analyzer.py:54-113`, `src/agents/analyzer.py:213-300`).

The “intelligence” is prompt-driven and role-specialized: prompts live in YAML templates (`src/agents/prompts/analyzer.yaml`, `src/agents/prompts/documenter.yaml`, `src/agents/prompts/ai_rules_generator.yaml`) and are rendered via Jinja in `PromptManager` (`src/utils/prompt_manager.py:9-95`). The AI-rules generation path is itself dual-agent concurrent execution (`MarkdownGenerator` + `CursorRulesGenerator`) orchestrated inside one agent class (`src/agents/ai_rules_generator.py:92-123`, `319-350`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker with concurrent workers** (a form of workflow orchestration), plus a sequential CLI stage chain (`analyze -> generate`).  
- Manager: handler classes and top-level agent classes (`AnalyzeHandler`, `AIRulesHandler`, `AnalyzerAgent`, `AIRulesGeneratorAgent`).  
- Workers: specialized role agents that run independently and return artifacts.

Control flow excerpt 1 (parallel analyzer workers): `src/agents/analyzer.py:54-63,111-114`
```python
if not self._config.exclude_code_structure:
    agent = self._structure_analyzer_agent
    agent_tasks[agent.name] = partial(self._run_agent, agent=agent, ...)

worker_pool = WorkerPool(max_workers=self._config.max_workers)
results = await worker_pool.run(list(agent_tasks.values()))
```

Control flow excerpt 2 (concurrent sub-generation tasks): `src/agents/ai_rules_generator.py:94-105`
```python
if not (skip_files["claude_md"] and skip_files["agents_md"]):
    tasks.append(self._run_markdown_generation(skip_files, existing_files))
if not skip_files["cursor_rules"]:
    tasks.append(self._run_cursor_rules_generation(existing_files))

results = await asyncio.gather(*tasks, return_exceptions=True)
```

## 4. Tools & External Integrations

- **LLM API (OpenAI-compatible endpoints)**: all agents call `OpenAIChatModel` through `OpenAIProvider` with configurable `base_url`, so it can target OpenAI/OpenRouter/local-compatible backends (`src/agents/analyzer.py:194-201`, `src/agents/documenter.py:132-139`, `src/agents/ai_rules_generator.py:280-287`).
- **Agent tools (filesystem)**:
  - `Read-File` tool for ranged file reads (`src/agents/tools/file_tool/file_reader.py:14-58`).
  - `List-Files-Tool` for recursive repository structure listing with ignore lists (`src/agents/tools/dir_tool/list_files.py:231-295`).
  - Wired into agents in `src/agents/analyzer.py:223-226`, `259-262`, etc.; `src/agents/documenter.py:161-163`; `src/agents/ai_rules_generator.py:329-331,346-348`.
- **Prompt templating**: Jinja2 + YAML prompt store (`src/utils/prompt_manager.py:5-7,69-95`).
- **Observability/tracing**: OpenTelemetry spans and optional Logfire instrumentation (`src/main.py:208-220`; tracing events across handlers/agents such as `src/agents/analyzer.py:151`, `src/handlers/analyze.py:23-35`).
- **GitLab automation**: `python-gitlab` for project discovery and MR creation (`src/handlers/cronjob.py:8-10,56-65,193-202`).
- **Git operations**: `gitpython` clone/branch/commit/push in cronjob flow (`src/handlers/cronjob.py:7,149-153,187-191`).
- **Retrying HTTP transport**: Tenacity-based retry wrapper used by model providers (`src/utils/retry_client.py:17-80`).

No MCP servers, browser automation, vector database, or RAG datastore integrations were found in source.

## 5. Notable Code Walkthrough

- `src/agents/analyzer.py:31-315` - Core multi-agent runtime: defines five analysis agents, renders role-specific prompts, runs workers concurrently via `WorkerPool`, and persists per-agent markdown outputs.
- `src/agents/ai_rules_generator.py:79-509` - Second-stage generation orchestrator: concurrently runs markdown and Cursor-rules generators, validates prerequisites (`.ai/docs`), then writes `CLAUDE.md`, `AGENTS.md`, and `.cursor/rules/*.mdc`.
- `src/agents/tools/file_tool/file_reader.py:10-58` - Primary LLM tool surface for grounded code reading; raises `ModelRetry` for recoverable errors to trigger tool retries.
- `src/handlers/cronjob.py:44-225` - End-to-end workflow automation over multiple GitLab projects: filter applicability, clone, analyze, commit/push, and open merge requests.
- `src/main.py:41-103,160-255` - CLI control plane that maps commands/subcommands to handlers and forms the executable workflow entrypoint.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. The repository operationalizes automation at two levels: (1) automated documentation pipeline steps (`analyze -> generate readme/ai-rules`) and (2) scheduled org-scale automation across GitLab repos with branch/MR lifecycle management (`src/handlers/cronjob.py:53-204`). Multi-agent LLM analysis is embedded as a reusable workflow stage rather than an interactive chat product. This is not primarily code generation or RAG retrieval; it is agentic process automation for documentation operations.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent specialization with distinct prompts and outputs (`src/agents/analyzer.py:213-300`, `src/agents/prompts/analyzer.yaml`).
  - Concurrency with error isolation/partial success handling (`src/agents/analyzer.py:117-148`; `src/utils/worker_pool.py:56-79`).
  - Strong operational integration for real CI-style workflows via GitLab MR automation (`src/handlers/cronjob.py:124-204`).
  - Structured outputs via Pydantic models for document generation (`src/agents/documenter.py:20-22`; `src/agents/ai_rules_generator.py:30-49`).
  - Built-in tracing and retry policies for production resilience (`src/main.py:208-220`; `src/utils/retry_client.py:57-80`).

- **Limitations:**
  - Limited toolset (read/list filesystem only); no code execution, search index, or web context tooling (`src/agents/tools/*`).
  - No long-term memory/caching; each run re-analyzes from scratch.
  - Framework dependency is tightly coupled to OpenAI-compatible chat interfaces despite “multiple LLM support” positioning (`src/agents/*` model setup).
  - In cronjob flow, push uses force (`repo.git.push(..., "-f")`), which can be risky in collaborative environments (`src/handlers/cronjob.py:191`).
  - No automated test suite validating agent behaviors/end-to-end outputs in repo source.

- **Research relevance:**
  - Practical example of **modular multi-agent decomposition** for software-analysis tasks.
  - Useful case of **artifact-producing MAS pipelines** (agents generate intermediate docs consumed by downstream agents).
  - Demonstrates **workflow-level orchestration + DevOps integration** (LLM agents embedded in MR automation loops).
  - Shows a prompt-template-driven governance pattern for deterministic documentation generation.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
