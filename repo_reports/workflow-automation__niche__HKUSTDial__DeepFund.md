---
repo_name: HKUSTDial/DeepFund
url: "https://github.com/HKUSTDial/DeepFund"
stars: 267
forks: 46
contributors_count: 7
last_commit_date: "2026-03-18T03:42:26+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 4
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T15:41:38.341937+00:00"
model: auto
duration_s: 103.8
clone_size_kb: 39144
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

DeepFund is a research-oriented multi-agent trading workflow that runs daily portfolio decision cycles over user-specified tickers by executing `python src/main.py --config ... --trading-date ...` with either Supabase or SQLite storage (`src/main.py:22-56`, `README.md:106-115`). For each ticker, it gathers market/fundamental/news/policy/insider/macroeconomic data, has multiple analyst agents generate structured bullish/bearish/neutral signals, and then a portfolio manager agent outputs a buy/sell/hold decision with shares (`src/agents/analysts/*.py`, `src/agents/portfolio_manager.py:14-99`). The system persists prompts, signals, decisions, and evolving portfolios in DB tables so runs are replayable and auditable (`src/database/interface.py:4-51`, `src/database/sqlite_helper.py:249-379`). In planner mode, an additional planner LLM first selects which analyst roles should execute for the ticker (`src/agents/planner.py:20-44`).

## 2. Agent Framework & Architecture

This repo **actually uses LangGraph + LangChain**, not CrewAI/AutoGen. Evidence: `StateGraph` is imported from `langgraph.graph` and compiled/invoked at runtime (`src/graph/workflow.py:2`, `src/graph/workflow.py:52-71`, `src/graph/workflow.py:114`), while LLM calls are made through LangChain chat model wrappers (`ChatOpenAI`, `ChatAnthropic`, `ChatDeepSeek`, etc.) with structured output (`src/llm/provider.py:5-10`, `src/llm/inference.py:56-62`). Dependencies also include `langgraph` and multiple `langchain-*` packages (`pyproject.toml:16-23`).

Architecturally, agents are plain Python functions registered in a central registry (`src/agents/registry.py:6-101`): six analyst roles (`technical`, `fundamental`, `insider`, `company_news`, `macroeconomic`, `policy`) plus a `portfolio manager`. Each analyst node pulls external data via API router, builds a role-specific prompt, and returns an `AnalystSignal`; signals are accumulated in graph state using `Annotated[List[AnalystSignal], operator.add]` (`src/graph/schema.py:67-83`).

The “intelligence” is mainly prompt-driven plus constrained structured outputs: prompts define role behavior (`src/llm/prompt.py:9-131`), and `agent_call` enforces Pydantic schemas via `with_structured_output(..., method="function_calling")` with retries (`src/llm/inference.py:42-70`). Optional planner logic is separate from the graph itself: before building the graph per ticker, `planner_agent` selects active analyst nodes from the configured pool (`src/graph/workflow.py:74-89`, `src/agents/planner.py:20-44`).

## 3. Orchestration Pattern

Closest pattern: **hierarchical (manager-worker) implemented as a LangGraph star workflow**.

- Worker layer: multiple analyst agents run first and emit signals.
- Manager layer: one portfolio manager consumes aggregated signals and issues final action.
- Optional meta-manager: planner chooses which workers participate before graph compilation.

Control flow in graph construction (`src/graph/workflow.py:56-68`):

```python
for analyst in self.current_analysts:
    graph.add_node(analyst, agent_func)
    graph.add_edge(START, analyst)
    graph.add_edge(analyst, AgentKey.PORTFOLIO)

graph.add_edge(AgentKey.PORTFOLIO, END)
```

Per-ticker execution loop, including planner gate then graph invoke (`src/graph/workflow.py:97-115`):

```python
for ticker in self.tickers:
    self.load_analysts(ticker)  # planner or all analysts
    state = FundState(...)
    workflow = self.build()
    final_state = workflow.invoke(state)
```

So this is not peer-to-peer swarming; it is centralized decision-making with specialist workers feeding one decision authority.

## 4. Tools & External Integrations

- **LLM providers (LangChain chat backends):** OpenAI, Anthropic, DeepSeek, Ollama, Fireworks, plus OpenAI-compatible endpoints for Alibaba/Zhipu/YiZhan/AiHubMix; wired in `src/llm/provider.py:20-77`, invoked in `src/llm/inference.py:17-65`.
- **LangGraph orchestration runtime:** state graph compile/invoke in `src/graph/workflow.py:52-71`, `src/graph/workflow.py:111-115`.
- **Financial market/news data APIs (HTTP via `requests`):**
  - Alpha Vantage (prices, fundamentals, insider trades, news, macro indicators) in `src/apis/alphavantage/api.py:15-227`.
  - Yahoo Finance alternative path in router (`src/apis/router.py:3-33`; class exists under `src/apis/yfinance/api.py`).
  - FinancialDatasets client exists but appears not used by current router path (`src/apis/financialdataset/api.py:10-57`).
- **Database/persistence layer:**
  - Supabase (default) client integration in `src/database/supabase_helper.py:9-266`.
  - SQLite local fallback in `src/database/sqlite_helper.py:11-385`.
  - Runtime switch in `src/util/db_helper.py:8-21` and CLI flag in `src/main.py:29-36`.
- **Local filesystem config loading:** YAML experiment config ingestion in `src/util/config.py:15-30`.
- **Not present:** no MCP integration, no browser automation, no shell-executing agent tools, no vector DB/RAG pipeline in runtime code.

## 5. Notable Code Walkthrough

- `src/graph/workflow.py:12-134` - Core runtime orchestrator. Initializes portfolio state from DB, optionally calls planner, builds LangGraph nodes/edges dynamically per ticker, invokes workflow, and applies resulting decisions back into portfolio.
- `src/agents/registry.py:6-101` - Agent catalog and abstraction point. Maps string keys to agent callables/docs, validates analyst keys, and is used by workflow builder for dynamic node registration.
- `src/agents/portfolio_manager.py:14-99` - Final decision authority. Pulls latest price, runs a risk-control LLM step to derive target position ratio, then runs decision LLM with memory and tradable-share constraints, and persists decisions.
- `src/agents/analysts/technical.py:46-95` (representative of analyst nodes) - Fetches candles, computes deterministic indicators (trend/RSI/volatility/etc.), then asks LLM to synthesize them into a structured signal and saves it.
- `src/llm/inference.py:42-70` - Shared LLM invocation contract. Converts config to provider model, enforces schema-constrained outputs with retries, and returns default model instances on failure for graceful degradation.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** is accurate. The system automates a repeatable multi-step investment research/decision pipeline: ingest config/date, load portfolio memory, run specialized analyst agents, aggregate outputs through a manager, update persistent portfolio state, and log every LLM artifact (`src/main.py:22-49`, `src/graph/workflow.py:91-134`, `src/database/interface.py:37-51`). This is a concrete automated operational workflow rather than generic chat, code synthesis, or retrieval-centric QA. It is also agentic because multiple coordinated LLM roles execute at runtime with explicit orchestration and role separation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear role-based multi-agent decomposition with explicit specialist functions and a final manager (`src/agents/registry.py:60-100`).
  - Real orchestration graph built dynamically per ticker/selected analysts (`src/graph/workflow.py:60-69`).
  - Strong structured-output discipline via Pydantic + function-calling reduces malformed agent outputs (`src/llm/inference.py:56-64`).
  - Good experiment traceability: prompts/signals/decisions/portfolio states persisted for replay/analysis (`src/database/sqlite_helper.py:249-379`).
  - Planner-mode toggles adaptive agent selection, enabling controllable compute-vs-coverage tradeoff (`src/graph/workflow.py:74-89`).

- **Limitations:**
  - Parallel analyst execution is implied by graph fan-out but no explicit concurrency controls/latency management; scale behavior unclear (`src/graph/workflow.py:64-65`).
  - API robustness is limited (minimal rate-limit/backoff handling; some `print` instead of structured logging in API client) (`src/apis/alphavantage/api.py:225-227`).
  - Planner trust boundary is weak: selected analyst names are returned by LLM and not revalidated post-selection before node creation.
  - Risk and allocation logic is heuristic/simple (e.g., fixed max ratio formula), which may constrain financial realism (`src/agents/portfolio_manager.py:36-41`).
  - Some integrations are stubbed or not wired in main path (e.g., JoinQuant TODO, FinancialDatasets client unused by router) (`src/apis/joinquant/api.py:1-4`, `src/apis/router.py:12-18`).

- **Research relevance:**
  - Useful evidence of a **production-style academic MAS** where multiple LLM roles are coupled with external non-LLM tools (market APIs + DB memory).
  - Demonstrates a practical hybrid design: deterministic feature extraction plus LLM judgment per role (`src/agents/analysts/technical.py:67-88`).
  - Offers a concrete case of **hierarchical agent governance** (planner -> analysts -> portfolio manager).
  - Supports studies on reproducibility/auditability in agent systems due to persisted prompts and decisions.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
