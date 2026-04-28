---
repo_name: TimeCopilot/timecopilot
url: "https://github.com/TimeCopilot/timecopilot"
stars: 449
forks: 65
contributors_count: 12
last_commit_date: "2026-04-20T21:41:05+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T15:35:40.685618+00:00"
model: auto
duration_s: 68.6
clone_size_kb: 15623
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`TimeCopilot/timecopilot` is a Python package/CLI that turns natural-language forecasting requests into an automated time-series workflow: feature extraction, model evaluation, forecast generation, anomaly detection, and explanation. Users typically run `timecopilot` interactively or `timecopilot forecast <csv-or-url>` (`timecopilot/_cli.py:351-399`) and receive both structured outputs (`fcst_df`, `eval_df`, etc.) and narrative analysis. Under the hood it combines an LLM-driven controller with many forecasting backends (statistical, neural, foundation models) via a unified forecaster API (`timecopilot/forecaster.py:32-710`). The main problem it solves is reducing manual model selection/tuning effort for forecasting and anomaly monitoring while still returning interpretable decisions.

## 2. Agent Framework & Architecture

The actual framework is **PydanticAI** (`from pydantic_ai import Agent`) rather than CrewAI/LangGraph (`timecopilot/agent.py:8`, `timecopilot/utils/experiment_handler.py:10-11`). I did not find LangGraph, CrewAI, AutoGen, or LlamaIndex orchestration imports in runtime code.

Architecture is a **custom multi-agent pipeline** implemented inside `TimeCopilot`:
- A forecasting agent with tool-calling (`self.forecasting_agent`) produces a typed `ForecastAgentOutput` (`timecopilot/agent.py:546-553`).
- A follow-up query agent (`self.query_agent`) answers questions over previously generated dataframes and can call `plot_tool` (`timecopilot/agent.py:597-624`).
- A dataset-parameter parser agent extracts `h/freq/seasonality` from natural language (`timecopilot/utils/experiment_handler.py:36-69`, `139-171`).
- A lightweight decision agent chooses whether a new user question should re-run analysis or just query existing results (`timecopilot/agent.py:1135-1192`).

The “intelligence” mainly lives in long system prompts plus tool interfaces in `timecopilot/agent.py`, while numerical forecasting logic lives in model wrappers and `TimeCopilotForecaster`.

## 3. Orchestration Pattern

Closest match: **hierarchical/sequential manager-worker pipeline** (not graph/swarm).  
A top-level manager class (`TimeCopilot`) coordinates specialized agents and deterministic tools in ordered stages.

Control-flow evidence:

`timecopilot/agent.py:1260-1264` (manager runs forecasting agent)
```python
result = self.forecasting_agent.run_sync(
    user_prompt=query,
    deps=self.dataset,
)
```

`timecopilot/agent.py:1365-1374` (routing between rerun vs query path)
```python
if self._maybe_rerun(query):
    self.analyze(df=self.dataset.df, query=query)

result = self.query_agent.run_sync(
    user_prompt=conversation_context,
    deps=self.dataset,
)
```

Within the forecasting agent, the prompt enforces ordered tool use (`tsfeatures_tool -> cross_validation_tool -> forecast_tool -> detect_anomalies_tool`) (`timecopilot/agent.py:477-517`), which is a sequential workflow policy rather than a state-machine graph.

## 4. Tools & External Integrations

- **LLM providers via PydanticAI model adapters**: model string like `openai:gpt-4o-mini` passed into all agents (`timecopilot/_cli.py:61-75`, `timecopilot/agent.py:423-551`).
- **Forecasting model backends (local libs)**: unified wrapper calls many model classes through `TimeCopilotForecaster` (`timecopilot/forecaster.py:104-158`, `249-333`, `435-531`).
- **Nixtla TimeGPT API (external HTTP service)**: `NixtlaClient` initialized with `NIXTLA_API_KEY` (`timecopilot/models/foundation/timegpt.py:6`, `104-113`, `179-187`).
- **Hugging Face model hub access**: e.g., TimesFM checks/loads repos via `huggingface_hub` (`timecopilot/models/foundation/timesfm.py:9`, `63-70`, `150-152`).
- **Distributed execution backends**: Fugue adapters for Spark/Dask/Ray (`timecopilot/forecaster.py:210-247`, `394-434`, `584-622`).
- **Data ingestion from URL/local files**: parser reads CSV/Parquet paths and HTTP URLs with `requests` (`timecopilot/utils/experiment_handler.py:72-100`).
- **Visualization/display tooling**: `plot_tool` uses matplotlib and shell utilities (`imgcat/catimg/timg/chafa`, `open`, `xdg-open`) (`timecopilot/agent.py:618-913`).

No MCP server integration or browser automation framework (Playwright/Selenium) is wired in runtime code.

## 5. Notable Code Walkthrough

- `timecopilot/agent.py:404-1692` - Core orchestration class defining multiple PydanticAI agents, tool functions, prompt contracts, output validation, and query/rerun routing; this is where agentic behavior is implemented.
- `timecopilot/utils/experiment_handler.py:36-171` - Defines a separate parser agent that extracts forecasting parameters from NL prompts and combines them with inferred defaults from the dataframe.
- `timecopilot/forecaster.py:32-710` - Unified model execution layer that runs forecast/cross-validation/anomaly workflows across many models and optionally distributed dataframes.
- `timecopilot/models/foundation/timegpt.py:39-191` - Representative external foundation-model integration using Nixtla’s hosted API and per-model aliasing into output columns.
- `timecopilot/_cli.py:91-407` - User-facing interactive/one-shot CLI loop that initializes `TimeCopilot`, executes analysis, and supports follow-up conversational querying.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** looks **partially wrong** after code inspection. It does run in terminal (CLI chat, file paths, shell image viewers), but the core system is not an agent that operates browsers or terminals as task environments; it is an automated forecasting pipeline with LLM-based planning/tool-use over time-series models (`timecopilot/_cli.py:351-399`, `timecopilot/agent.py:935-1077`). The better category is **Workflow Automation**: it automates a multi-step analytic workflow (parameter parsing, feature extraction, CV, model selection, forecasting, anomaly detection, explanation) from one user request.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear role separation across multiple agents (parser, forecasting, query, rerun-decision) with typed outputs (`timecopilot/agent.py`, `timecopilot/utils/experiment_handler.py`).
  - Strong tool grounding in concrete analytics functions (CV, forecasting, anomalies) rather than pure text generation (`timecopilot/agent.py:971-1077`).
  - Broad backend ecosystem (classical + TS foundation models + distributed execution) behind one interface (`timecopilot/forecaster.py`).
  - Runtime guardrails via output validation and retry (`ModelRetry`) to enforce baseline quality checks (`timecopilot/agent.py:1079-1091`).
  - Practical CLI UX for iterative analysis and follow-up Q&A (`timecopilot/_cli.py:182-317`).

- **Limitations:**
  - Orchestration is prompt-driven sequencing rather than explicit workflow graph/state machine; behavior depends on LLM compliance (`timecopilot/agent.py:458-537`).
  - Decision-to-rerun logic uses another LLM boolean classifier, which can introduce routing instability (`timecopilot/agent.py:1135-1192`).
  - Limited formal tests for multi-tool interaction order and end-to-end agent behavior; tests are relatively shallow stubs (`tests/test_agent.py:11-47`).
  - Heavy dependency surface and many model backends may complicate reproducibility/deployment (`pyproject.toml:60-107`).
  - No explicit cost/latency-aware planner for selecting among expensive models/providers.

- **Research relevance:**
  - Useful example of **modular multi-agent decomposition** in a domain workflow (specialized LLM roles + deterministic tools).
  - Demonstrates **typed agent outputs + tool-calling** for robust structured analytics pipelines.
  - Illustrates hybrid architecture where LLM planning controls non-LLM scientific models.
  - Good case study for evaluating prompt-enforced orchestration versus explicit graph-based control.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
