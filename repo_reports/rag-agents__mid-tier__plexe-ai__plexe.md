---
repo_name: plexe-ai/plexe
url: "https://github.com/plexe-ai/plexe"
stars: 2565
forks: 254
contributors_count: 9
last_commit_date: "2026-03-05T21:56:18+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T15:03:48.107698+00:00"
model: auto
duration_s: 88.3
clone_size_kb: 7194
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`plexe` is an automated ML-building system that turns a natural-language intent plus a dataset URI into a trained, packaged model artifact. A user runs `python -m plexe.main --train-dataset-uri ... --intent "..." --spark-mode ...`, and the workflow performs data analysis, splitting/sampling, baseline generation, iterative model search, optional final evaluation, and packaging (`plexe/main.py:38-66`, `plexe/workflow.py:107-125`). The output is a `model/` package (and optionally `model.tar.gz`) containing model artifacts, inference code, reports, and metadata (`plexe/workflow.py:1980-2005`). Rather than a chat agent, it is an autonomous multi-phase ML pipeline where LLM agents generate and validate intermediate ML decisions and code. It solves “AutoML from prompt” with explicit state/checkpointing and resumability.

## 2. Agent Framework & Architecture

This repo is **not** LangGraph/LangChain/CrewAI/AutoGen; it is a **custom multi-agent architecture built on `smolagents`**. Evidence: agent classes instantiate `smolagents.CodeAgent` and use `smolagents.tool`-decorated tool functions (`plexe/agents/planner.py:9-11`, `plexe/agents/hypothesiser.py:9-11`, `plexe/tools/submission.py:14`, `plexe/agents/model_evaluator.py:13-15`). LLM calls are routed through a custom `PlexeLiteLLMModel` wrapper around `smolagents.LiteLLMModel` with retry logic (`plexe/utils/litellm_wrapper.py:45-114`).

Architecture is a 6-phase orchestrated pipeline with many specialized agents invoked by the central workflow: layout detection, statistical analysis, task analysis, metric selection/implementation, split/sampling, baseline builder, then iterative search agents (hypothesiser/planner/feature processor/model definer/insight extractor), and final evaluation agent (`plexe/workflow.py:46-59`, `plexe/workflow.py:781-877`, `plexe/workflow.py:1461-1611`). The “intelligence” is mostly in large role-specific prompts built inside each agent class plus constrained tool APIs that write validated outputs into shared `BuildContext.scratch` (`plexe/agents/planner.py:55-199`, `plexe/agents/feature_processor.py:168-248`, `plexe/tools/submission.py:76-166`).

State is explicit and persistent: `BuildContext`, `SearchJournal` (solution DAG), and `InsightStore`; checkpoints are loaded/saved between phases for resume/pause workflows (`plexe/workflow.py:165-199`, `plexe/workflow.py:876-877`, `plexe/workflow.py:1640-1647`).

## 3. Orchestration Pattern

Closest match: **hierarchical + sequential workflow with an iterative tree-search inner loop** (custom orchestrator, not graph runtime). A top-level controller (`build_model`) runs phases in order and conditionally pauses/resumes (`plexe/workflow.py:225-315`). Inside phase 4, policy + agents form a manager-worker loop: policy picks a node, hypothesiser/planner generate plans, and worker agents execute variants in parallel.

```1462:1470:plexe/workflow.py
# Step 2a: Policy Picks Node to Expand
parent_node = search_policy.decide_next_solution(journal, context, iteration, config.max_search_iterations)
expand_solution_id = parent_node.solution_id if parent_node else None

logger.info(
    f"Expanding solution {expand_solution_id if expand_solution_id is not None else 'from scratch'}"
)
```

```1504:1538:plexe/workflow.py
# Hypothesis-driven mode: Generate hypothesis then plans
hypothesis = HypothesiserAgent(
    journal=journal, context=context, config=config, expand_solution_id=expand_solution_id,
).run()

plans = PlannerAgent(
    journal=journal, context=context, config=config, hypothesis=hypothesis,
).run()
```

Execution then fans out via threads (`ThreadPoolExecutor`) for variants and returns to centralized journal/insight updates (`plexe/workflow.py:1552-1594`, `plexe/workflow.py:1602-1611`). So this is not swarm/peer-to-peer; control is centralized.

## 4. Tools & External Integrations

- **LLM providers via LiteLLM**: every agent uses `PlexeLiteLLMModel` (`smolagents` + LiteLLM) with configurable routing/api headers and retry (`plexe/agents/planner.py:188-193`, `plexe/utils/litellm_wrapper.py:45-114`, `plexe/config.py:267-275`, `plexe/config.py:509-554`).
- **Agent tooling (internal, constrained function calls)**: agents can call only explicitly injected tools (no base tools) such as `save_plan`, `save_hypothesis`, `save_pipeline_code`, evaluation registrars (`plexe/agents/planner.py:195-197`, `plexe/agents/model_evaluator.py:127-133`, `plexe/tools/submission.py:76-166`, `plexe/tools/submission.py:1238-1774`).
- **Data processing backend**: Spark local or Databricks Connect (`plexe/execution/dataproc/session.py:45-49`, `plexe/execution/dataproc/session.py:144-237`).
- **Storage integration**: local filesystem + optional S3 durable storage/checkpoints/model upload via `StandaloneIntegration`; Azure/GCS are stubs (`plexe/integrations/standalone.py:21-29`, `plexe/integrations/standalone.py:115-164`, `plexe/integrations/storage/azure.py`, `plexe/integrations/storage/gcs.py`).
- **Observability**: OpenTelemetry + Smolagents instrumentor (`plexe/utils/tracing.py:34-57`).
- **Not present**: no vector DB, retrieval pipeline, browser automation, terminal-use agents, MCP servers, or web-search tools in runtime agent logic.

## 5. Notable Code Walkthrough

- `plexe/workflow.py:107-350` - Master orchestrator: checkpoint resume, phase sequencing, pause points, and wiring for all specialized agents; this is the runtime backbone.
- `plexe/workflow.py:1375-1649` - Iterative tree-search loop combining policy decisions, hypothesis/planning, parallel variant execution, and insight extraction; this is the core multi-agent coordination logic.
- `plexe/agents/planner.py:55-239` - Representative agent implementation: builds role prompt, injects one constrained tool, runs `CodeAgent`, and reads structured outputs from context.
- `plexe/tools/submission.py:76-166` - Tool contract pattern: validates agent-generated code (`exec` + pipeline checks) before mutating shared state; shows guardrails around LLM outputs.
- `plexe/utils/litellm_wrapper.py:45-114` - LLM abstraction layer adding retries, header injection, and call hooks; critical for production robustness of agent calls.

## 6. Use-Case Mapping

The upstream assignment (**RAG + Agents**) appears **incorrect** for this codebase. This repo clearly has **multiple coordinated runtime agents**, but there is no retrieval-augmented generation stack (no retriever/index/vector store/doc corpus path). Instead, agents automate an end-to-end ML build workflow: analyze data, propose experiments, generate feature/model code, train/evaluate, and package outputs (`plexe/workflow.py:781-877`, `plexe/workflow.py:1461-1649`). The better category is **Workflow Automation** (agentic AutoML pipeline orchestration).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear role-specialized multi-agent decomposition with explicit handoff artifacts (`plexe/workflow.py:46-59`).
  - Strong guardrails: tool-based structured submissions plus validation before acceptance (`plexe/tools/submission.py:76-166`).
  - Practical robustness features: retries around LLM calls, checkpointing/resume, and policy-driven search (`plexe/utils/litellm_wrapper.py:77-114`, `plexe/workflow.py:165-199`).
  - Hybrid execution design: agent reasoning + deterministic training/evaluation infrastructure (Spark + runners) (`plexe/workflow.py:1271-1347`).
  - Supports controlled concurrency in search variants (`plexe/workflow.py:1552-1584`).

- **Limitations:**
  - No true RAG/retrieval capability despite “agentic” framing.
  - Some non-tabular pathways are noted as TODOs; feature processor is still tabular-centric (`plexe/agents/feature_processor.py:87-91`).
  - `save_pipeline_code` executes arbitrary generated Python (`exec`), which is risky in less-trusted environments (`plexe/tools/submission.py:126-133`).
  - Evaluation and some fitting steps rely on samples with explicit quality caveats for very large datasets (`plexe/workflow.py:1682-1689`, `plexe/agents/model_evaluator.py:41-48`).
  - Cloud storage portability incomplete: Azure/GCS helpers are stubs (`plexe/integrations/storage/azure.py`, `plexe/integrations/storage/gcs.py`).

- **Research relevance:**
  - Good case study of **manager-orchestrated multi-agent AutoML** with explicit memory artifacts (journal + insights).
  - Demonstrates **tool-constrained agent design** for safer code generation and structured outputs.
  - Illustrates **policy + LLM co-control** (algorithmic search policy selects expansion; LLM agents propose plans).
  - Useful for studying **reliability patterns** in agent systems (checkpointing, retries, observability hooks).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
