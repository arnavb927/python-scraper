---
repo_name: martymcenroe/AssemblyZero
url: "https://github.com/martymcenroe/AssemblyZero"
stars: 85
forks: 0
contributors_count: 3
last_commit_date: "2026-04-22T23:26:21+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 4
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents]
generated_at: "2026-04-27T15:53:47.694391+00:00"
model: auto
duration_s: 115.2
clone_size_kb: 211771
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

AssemblyZero is a Python-based multi-agent orchestration system that automates a software delivery pipeline from GitHub issue to implementation PR, with checkpoints and governance gates. In practice, users run CLIs like `tools/run_requirements_workflow.py`, `tools/run_implement_from_lld.py`, or `tools/orchestrate.py` to execute end-to-end workflows. The system produces concrete artifacts (issue briefs, LLD/spec markdown, generated code/tests, lineage/audit logs, and optionally PRs) rather than just chat responses. It combines Claude and Gemini roles across drafting, review, implementation, and adversarial validation. The project’s core value is controlled automation of engineering workflow steps with retry logic, guardrails, and resumability.

## 2. Agent Framework & Architecture

The repo **does use LangGraph directly** as the orchestration framework (`langgraph` dependency in `pyproject.toml:12-14`, graph construction in files like `assemblyzero/workflows/requirements/graph.py:49-63` and `assemblyzero/workflows/testing/graph.py:62-90`). It is **not primarily CrewAI/AutoGen/LlamaIndex**. LangChain appears only in limited spots (e.g., `assemblyzero/workflows/lld/nodes/assembly_node.py:6-7`) and is not the main orchestration runtime.

Architecture is layered: a top-level orchestrator graph (`assemblyzero/workflows/orchestrator/graph.py:160-187`) runs stage runners (`triage`, `lld`, `spec`, `impl`, `pr` in `assemblyzero/workflows/orchestrator/stages.py:432-439`), and each stage invokes another LangGraph sub-workflow (requirements/spec/testing). “Intelligence” lives in (a) node prompts and role-specific system prompts (e.g., drafter/reviewer in requirements nodes), (b) routing functions over shared graph state, and (c) a custom LLM provider abstraction handling Claude CLI, Anthropic API fallback, and Gemini (`assemblyzero/core/llm_provider.py:244-283`, `1338-1387`).

It is genuinely multi-agent at runtime: separate role agents include drafter, reviewer, implementation coder, test-plan reviewer, and adversarial Gemini checker (`assemblyzero/workflows/requirements/nodes/generate_draft.py:103-108`, `review.py:89-94`; `assemblyzero/workflows/testing/nodes/adversarial_node.py:1-11`).

## 3. Orchestration Pattern

Closest match: **graph/state-machine orchestration with hierarchical composition** (manager graph invoking subgraphs).

Control flow is explicitly encoded with conditional edges and loopbacks in LangGraph. Example from requirements workflow (`assemblyzero/workflows/requirements/graph.py:546-558`):

```python
graph.add_conditional_edges(
    N3_REVIEW,
    route_after_review,
    {
        "N4_human_gate_verdict": N4_HUMAN_GATE_VERDICT,
        "N5_finalize": N5_FINALIZE,
        "N1_generate_draft": N1_GENERATE_DRAFT,
        "N3_review": N3_REVIEW,
        "HALT": HALT,
    },
)
```

Top-level orchestration routes between stages, retrying or terminating based on stage results (`assemblyzero/workflows/orchestrator/graph.py:175-185`):

```python
workflow.add_conditional_edges(
    "run_stage",
    _route_after_stage,
    {
        "run_stage": "run_stage",
        "done": "done",
        "terminal": "terminal",
    },
)
workflow.add_edge("done", END)
```

So this is not a peer-to-peer swarm; it is centrally controlled graph orchestration with nested workflows.

## 4. Tools & External Integrations

- **LLM providers (Claude/Gemini/Anthropic API fallback):** unified provider layer with model routing, retries, circuit breaker, schema output (`assemblyzero/core/llm_provider.py:311-417`, `643-764`, `1072-1188`, `1338-1387`).
- **Claude CLI execution:** subprocess-based `claude -p` calls with JSON output and prompt/tool settings (`assemblyzero/core/llm_provider.py:447-456`).
- **Gemini API client:** used for reviewer/analysis/adversarial calls (`assemblyzero/core/llm_provider.py:1131-1163`, `assemblyzero/workflows/scout/nodes.py:262-269`).
- **Git/GitHub CLI automation:** issue listing, auth token, branch/worktree management, PR creation (`tools/run_requirements_workflow.py:238-246`; `tools/run_implement_from_lld.py:101-164`; `assemblyzero/workflows/orchestrator/stages.py:383-405`).
- **PyGithub API:** repo search/readme/license retrieval in Scout workflow (`assemblyzero/workflows/scout/nodes.py:13`, `104-126`, `167-180`).
- **Shell/test execution:** command runner and framework-specific test runners (pytest/jest/playwright via subprocess/npx) (`assemblyzero/workflows/testing/runners/playwright_runner.py:44-53`).
- **Checkpoint persistence (SQLite):** LangGraph `SqliteSaver` for resumable runs (`tools/run_requirements_workflow.py:101-107`; `tools/run_implement_from_lld.py:601`, `779-781`).
- **Optional RAG vector store (ChromaDB):** persistent embedding store wrapper for librarian retrieval (`assemblyzero/rag/vector_store.py:1-9`, `55-61`, `170-174`).
- **Telemetry/tracing:** LangSmith setup + internal telemetry emitters (`tools/run_requirements_workflow.py:46-52`; `run_implement_from_lld.py:54-61`).

## 5. Notable Code Walkthrough

- `assemblyzero/workflows/orchestrator/graph.py:160-324` - Defines the meta-graph that runs the full pipeline and handles retries, locks, resume, and terminal failure/success conditions.
- `assemblyzero/workflows/orchestrator/stages.py:99-439` - Implements per-stage runners and bridges between top-level orchestration and subgraphs (`requirements`, `implementation_spec`, `testing`), plus git/PR actions.
- `assemblyzero/workflows/requirements/graph.py:430-575` - Core drafting/review governance graph with loops, human gates, and HALT routing; this is where manager-worker style iteration is concretely encoded.
- `assemblyzero/workflows/requirements/nodes/generate_draft.py:70-257` - Drafter agent node: builds large context-rich prompts, selects provider, enforces budget/prompt caps, and writes lineage artifacts.
- `assemblyzero/workflows/testing/nodes/implementation/orchestrator.py:275-689` - Code generation execution engine: file-level prompting, model routing, retries, mechanical validation, path guardrails, and atomic writes.
- `assemblyzero/workflows/testing/nodes/adversarial_node.py:50-215` - Gemini adversarial checker that analyzes generated implementation, emits extra tests, validates them, and feeds verdicts back into the workflow.

## 6. Use-Case Mapping

Although the repository clearly performs **code generation** (e.g., implementation node writes code files from LLD specs in `assemblyzero/workflows/testing/nodes/implementation/orchestrator.py:573-643`), its broader system behavior is better categorized as **Workflow Automation**. The dominant design is not “single coding agent,” but orchestrated multi-stage governance across issue triage, design drafting, review, implementation, testing, and PR creation (`assemblyzero/workflows/orchestrator/state.py:53-62`, `stages.py:432-439`). So the upstream “Code Generation” label is partially true at the node level, but the repo-level primary use case is workflow automation over software delivery.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong explicit control flow with LangGraph conditional routing and loop guards (`requirements/graph.py`, `testing/graph.py`).
  - Real production-style orchestration concerns: resumability, locks, retries, stage artifacts (`orchestrator/graph.py:223-324`).
  - Multi-provider abstraction with policy/fallback/circuit-breaker controls (`core/llm_provider.py:944-1070`).
  - Integrates human gates and automated gates in the same state machine (`requirements/graph.py:256-279`, `383-406`).
  - Rich operational tooling (worktrees, PR creation, status files, audit lineage).

- **Limitations:**
  - Heavy complexity and many workflow-specific branches can make reasoning/debugging difficult.
  - Some architecture appears transitional (LangChain node exists but seems separate from primary runtime path).
  - Strong dependence on local CLI/tooling environment (`claude`, `gh`, git worktrees, Node for Playwright).
  - Token/cost controls are extensive but still mostly heuristic caps and truncation strategies.
  - “Agent” behavior is mostly role prompts + routing; limited autonomous planning beyond predefined state transitions.

- **Research relevance:**
  - Good evidence of **hierarchical multi-agent orchestration** in practical software engineering pipelines.
  - Useful case study for **guardrailed agent workflows** (human gates + mechanical validators + halt policies).
  - Demonstrates hybrid provider reliability patterns (CLI-first with API fallback and circuit breaking).
  - Illustrates how MAS ideas translate into artifact-centric CI/CD-style automation rather than chat UX.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
