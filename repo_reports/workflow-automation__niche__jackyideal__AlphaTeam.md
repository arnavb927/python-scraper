---
repo_name: jackyideal/AlphaTeam
url: "https://github.com/jackyideal/AlphaTeam"
stars: 252
forks: 35
contributors_count: 3
last_commit_date: "2026-04-19T13:34:42+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T17:41:17.872316+00:00"
model: auto
duration_s: 92.2
clone_size_kb: 10202
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`AlphaTeam` is a Flask-based multi-agent stock-research and portfolio-decision system inside the broader `AlphaFin` app, where users run `python app.py` (or `flask run`) and interact through `/team` plus API routes (`AlphaFin/app.py:1-27`, `AlphaFin/ai_team/routes.py:1-24`). The runtime creates seven specialized agents (director, analyst, intel, quant, risk, auditor, restructuring) and coordinates them to analyze questions, review risk, and produce a final synthesized report (`AlphaFin/ai_team/core/agent_registry.py:115-149`). It is not just chat: the team can call structured tools for market data, technical/fundamental analysis, portfolio state, risk warnings, SQL read queries, inter-agent messaging, and skill execution (`AlphaFin/ai_team/core/tool_registry.py:23-442`). In practice, users get an orchestrated workflow with traceable intermediate activity and governance controls (timeouts, stop, audit endpoints), rather than a single LLM response (`docs/ARCHITECTURE.md:109-169`).

## 2. Agent Framework & Architecture

This repo does **not** use CrewAI/LangGraph/AutoGen/LlamaIndex in runtime code. Core execution is a **custom framework** built around:
- custom `Agent` class with tool-calling loop (`AlphaFin/ai_team/core/agent.py:53-1300+`),
- custom `Orchestrator` scheduler (`AlphaFin/ai_team/core/orchestrator.py:72-1239+`),
- custom `MessageBus` for inter-agent messages (`AlphaFin/ai_team/core/message_bus.py:15-147`),
- custom registry-driven tool layer (`AlphaFin/ai_team/core/tool_registry.py:23-1801`).

LLM calls are OpenAI-compatible HTTP/Qwen-style calls, not a third-party agent framework abstraction (`AlphaFin/ai_team/core/agent.py:20-23`, `AlphaFin/services/ai_chat_service.py:19-47`, `AlphaFin/services/ai_chat_service.py:219-239`). Agent role intelligence is mainly encoded in large per-role system prompts and runtime planning logic (`AlphaFin/ai_team/agents/decision_director.py:7-63`, similar files in `AlphaFin/ai_team/agents/*`).

Architecturally, the orchestrator sets a staged workflow: director routing and task decomposition, phase-1 specialist research, phase-2 risk/audit evaluation, optional meeting, then director synthesis (`AlphaFin/ai_team/core/orchestrator.py:930-1235`). Each agent runs a bounded tool-usage loop with budget/timing constraints and can exchange messages through `send_message_to_agent` over the message bus (`AlphaFin/ai_team/core/agent.py:902-1319`, `AlphaFin/ai_team/core/tool_registry.py:256-268`, `AlphaFin/ai_team/core/tool_registry.py:1483-1525`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with phased parallel workers**.

Why: a director-centered orchestrator routes and assigns tasks, then executes specialist phases in parallel, then converges to director synthesis (`AlphaFin/ai_team/core/orchestrator.py:983-1235`). This is not peer swarm: control authority is centralized in orchestrator + director.

Example flow excerpt (assignment + phased parallel execution):
```911:1140:AlphaFin/ai_team/core/orchestrator.py
def run_cycle(self, topic=None, time_limit_seconds=None):
    ...
    director = get_agent('director')
    routing = self._route_task(director, topic, session_id)
    ...
    self._run_parallel(phase1_agents, session_id, topic, agent_assignments=agent_tasks)
    ...
    self._run_parallel(phase2_agents, session_id, agent_assignments=agent_tasks)
```

Example agent tool loop excerpt (worker execution logic):
```1160:1287:AlphaFin/ai_team/core/agent.py
use_tools_for_step = step_tool_round_limit > 0 and remaining_tool_rounds > 0
response = self._call_qwen(messages, use_tools=use_tools_for_step)
...
for tc in tool_calls:
    tool_name = func.get('name', '')
    ...
    result = execute_tool(tool_name, arguments, agent_id=self.agent_id, message_bus=bus, ...)
    messages.append({'role': 'tool', 'tool_call_id': tc.get('id', ''), ...})
```

## 4. Tools & External Integrations

- **LLM providers (Qwen via OpenAI-compatible API)**: Agent and chat services call Qwen endpoints using API key/base URL config (`AlphaFin/ai_team/core/agent.py:20-26`, `AlphaFin/services/ai_chat_service.py:23-47`, `AlphaFin/services/ai_chat_service.py:219-239`).
- **Kimi/Moonshot web search**: `web_search` tool delegates to Kimi `$web_search` pipeline for external retrieval (`AlphaFin/ai_team/core/tool_registry.py:117-127`, `AlphaFin/ai_team/core/tool_registry.py:912-977`, `AlphaFin/services/ai_chat_service.py:61-76`).
- **Market data APIs**: Tushare is a core dependency and runtime source for daily/minute/index/industry/news/quotes (`AlphaFin/services/stock_service.py:6-16`, `AlphaFin/ai_team/services/tushare_watch_service.py:24-31`, `AlphaFin/ai_team/services/tushare_watch_service.py:153-258`).
- **Public market quote fallbacks**: QQ and Sina HTTP quote endpoints are used when Tushare realtime access is unavailable (`AlphaFin/ai_team/services/tushare_watch_service.py:63-150`, `AlphaFin/ai_team/services/tushare_watch_service.py:249-256`).
- **Local databases (SQLite)**: portfolio and market caches are stored/queried locally; tool layer exposes read-only SQL via `query_database` (`AlphaFin/ai_team/core/portfolio_manager.py:39-174`, `AlphaFin/ai_team/core/tool_registry.py:237-251`, `AlphaFin/ai_team/core/tool_registry.py:1440-1480`).
- **Inter-agent messaging bus**: `send_message_to_agent` dispatches via `MessageBus` and can trigger target-agent processing (`AlphaFin/ai_team/core/message_bus.py:31-48`, `AlphaFin/ai_team/core/tool_registry.py:1483-1525`).
- **Skill sandbox + indicator execution**: agents can create/execute constrained Python skills and run indicator modules with optional vision summarization (`AlphaFin/ai_team/core/tool_registry.py:298-351`, `AlphaFin/ai_team/core/tool_registry.py:1357-1438`).
- **No MCP/browser automation/terminal agent tools**: no MCP server wiring, Playwright/browser control, or shell-execution agent tool surface found in core runtime code.

## 5. Notable Code Walkthrough

- `AlphaFin/ai_team/core/orchestrator.py:72-1239`  
  Central workflow engine: initializes specialist groups, handles session deadlines/overtime, routes tasks, executes phase-1 and phase-2 parallel agent runs, optionally convenes meetings, and triggers final director synthesis.

- `AlphaFin/ai_team/core/agent.py:53-1319`  
  Per-agent runtime: builds context/prompt profile, plans substeps, runs iterative LLM + function-calling loops, enforces tool/budget constraints, logs trace spans, and stores conversation/tool evidence.

- `AlphaFin/ai_team/core/tool_registry.py:23-590, 1440-1801`  
  Declares function-calling schema and dispatch function for all tools (market data, web search, SQL, messaging, portfolio actions, memory/skills), making it the key bridge between language reasoning and executable actions.

- `AlphaFin/ai_team/core/portfolio_manager.py:29-553, 635-805`  
  Implements the governed trading workflow and state machine: signal submission, risk review, director approval, execution, holdings/NAV updates, compensation/penalty logic, and risk-warning verification.

- `AlphaFin/ai_team/core/agent_registry.py:115-149`  
  Materializes the multi-agent team by instantiating all role agents with API keys, role prompts, and per-agent model settings; this is where the runtime MAS topology is concretely assembled.

## 6. Use-Case Mapping

The assigned label **`Workflow Automation` is appropriate**. This repository automates a structured, multi-step decision workflow: task intake -> routing/decomposition -> phased specialist execution -> risk/audit review -> final synthesis -> optional portfolio action (`docs/ARCHITECTURE.md:113-119`, `AlphaFin/ai_team/core/orchestrator.py:930-1235`, `AlphaFin/ai_team/core/portfolio_manager.py:238-374`). The “workflow” is explicit in code (session states, deadlines, parallel phases, approval gates), not just implicit prompting. It is finance-domain specific, but architecturally it is still workflow automation driven by coordinated LLM agents.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear role decomposition with explicit coordinator/specialist/reviewer separation (`docs/ARCHITECTURE.md:99-107`).
  - Real orchestration controls (timeouts, stop/resume, progress states), not a naïve chain (`AlphaFin/ai_team/core/orchestrator.py:203-317`).
  - Rich tool protocol and governance-minded execution surface (structured tool schemas + status handling) (`AlphaFin/ai_team/core/tool_registry.py:23-590`).
  - Traceability emphasis via activity bus and trace run/span hooks (`AlphaFin/ai_team/core/message_bus.py:76-114`, `AlphaFin/ai_team/core/agent.py:1198-1310`).
  - Domain-grounded approval workflow (risk then director gate) tied to persistent portfolio state (`AlphaFin/ai_team/core/portfolio_manager.py:328-374`).

- **Limitations:**
  - Heavy prompt-centric control; limited formal policy/verification beyond prompt and basic guards (e.g., no strict typed planner or formal validator layer).
  - Large monolithic files (`agent.py`, `tool_registry.py`, `orchestrator.py`) may hinder maintainability and independent testing granularity.
  - Coupling to specific providers/data services (Qwen/Kimi/Tushare) increases operational fragility under API/permission changes.
  - Limited evidence of robust automated tests for orchestration correctness and failure-mode regressions.
  - Significant logic and prompts are Chinese-specific and A-share specific, reducing portability without adaptation.

- **Research relevance:**
  - Practical evidence of **hierarchical multi-agent orchestration** with phased parallelism in production-style code.
  - Useful case for studying **governance controls** (timeout/overtime/stop, approvals, trace logs) in agentic systems.
  - Demonstrates integration of **tool-augmented agents + persistent transactional state** (portfolio DB) rather than stateless QA.
  - Illustrates a hybrid of social coordination (message bus, role prompts) and procedural workflow control.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
