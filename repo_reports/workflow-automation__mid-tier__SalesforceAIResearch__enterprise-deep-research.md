---
repo_name: SalesforceAIResearch/enterprise-deep-research
url: "https://github.com/SalesforceAIResearch/enterprise-deep-research"
stars: 1156
forks: 180
contributors_count: 5
last_commit_date: "2026-01-30T17:35:34+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 6
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T12:55:50.469777+00:00"
model: auto
duration_s: 93.9
clone_size_kb: 12401
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`SalesforceAIResearch/enterprise-deep-research` is a backend-heavy “deep research” system that runs a multi-step LLM research workflow over web/data sources and returns either a final report or a concise QA-style answer. A user typically calls the FastAPI endpoint `POST /deep-research`, optionally in streaming mode, and receives incremental events plus final synthesized output (`routers/research.py:28-117`, `app.py:26-147`). Under the hood, it decomposes a topic into subtasks, executes specialized searches/tools, iterates with reflection loops, and then compiles results into a polished output (`src/agent_architecture.py:1002-1270`, `src/graph.py:5189-5276`). It also supports steering/todo-guided research, file/database uploads, and text-to-SQL over uploaded datasets (`src/prompts.py:148-205`, `src/agent_architecture.py:2214-2330`, `app.py:135-145`).

## 2. Agent Framework & Architecture

The repo **actually uses LangGraph + LangChain**, plus custom agent classes. This is confirmed by imports and runtime graph construction: `from langgraph.graph import START, END, StateGraph` in `src/graph.py:73`, and LangChain model/tool classes in `llm_clients.py:15-22` and `src/tools/search_tools.py:15-17`.

Architecture is manager-worker with graph orchestration. The LangGraph state machine (`create_graph`) wires nodes like `multi_agents_network`, `generate_report`, `reflect_on_report`, `validate_context_sufficiency`, and finalization nodes (`src/graph.py:5189-5276`). The `multi_agents_network` entrypoint delegates to `MasterResearchAgent.execute_research`, which handles planning, task decomposition, subtask execution, and loop updates (`src/graph.py:284-415`, `src/agent_architecture.py:1002-1267`).

“Intelligence” is split across (a) large prompt templates and tool-selection policies (`src/prompts.py:4-260`), (b) planner/manager logic in `MasterResearchAgent` (`src/agent_architecture.py:29-48`, `:443-1002`), and (c) reflection/routing logic in graph nodes and conditional edges (`src/graph.py:3138-3196`, `:5248-5274`). Operationally, there are multiple specialized agents/components: `MasterResearchAgent`, `SearchAgent`, `VisualizationAgent`, and `ResultCombiner` (`src/agent_architecture.py:29-33`, `:2134-2140`, `:2451-2457`).

## 3. Orchestration Pattern

Closest fit: **graph + hierarchical (manager-worker hybrid)**.

- **Graph**: LangGraph controls node transitions, loops, and conditional routing (`src/graph.py:5194-5276`).
- **Hierarchical**: within `multi_agents_network`, a master agent plans/delegates search subtasks to specialized workers (`src/graph.py:366-415`, `src/agent_architecture.py:1516-1737`).

Code excerpt 1 (graph wiring / control flow):
`src/graph.py:5202-5255`
```python
builder.add_node("multi_agents_network", async_multi_agents_network)
builder.add_node("generate_report", generate_report)
builder.add_node("reflect_on_report", reflect_on_report)
...
builder.add_conditional_edges(
    "multi_agents_network",
    route_after_multi_agents_decision,
    {"validate_context_sufficiency": "validate_context_sufficiency",
     "generate_report": "generate_report"},
)
builder.add_conditional_edges("reflect_on_report", route_research, {
    "multi_agents_network": "multi_agents_network",
    "finalize_report": "finalize_report",
})
```

Code excerpt 2 (manager delegating tool tasks):
`src/agent_architecture.py:1544-1592`
```python
search_agent = SearchAgent(self.config, database_info=self.database_info)

if tool_name == "general_search":
    search_result = await search_agent.general_search(query_text)
elif tool_name == "academic_search":
    search_result = await search_agent.academic_search(query_text)
elif tool_name == "github_search":
    search_result = await search_agent.github_search(query_text)
elif tool_name == "linkedin_search":
    search_result = await search_agent.linkedin_search(query_text)
elif tool_name == "text2sql":
    search_result = await search_agent.text2sql_search(query_text)
```

## 4. Tools & External Integrations

- **Web search (Tavily API)**: core retrieval goes through `TavilyClient` and Tavily API key in `general_deep_search` (`src/utils.py:7`, `:153-206`, `:175-177`).
- **Specialized search tools (LangChain BaseTool wrappers)**: `general_search`, `academic_search`, `github_search`, `linkedin_search` implemented as tools and registered centrally (`src/tools/search_tools.py:38-49`, `src/tools/registry.py:37-74`).
- **Database/text2sql over uploaded files**: `Text2SQLTool` converts NL→SQL and executes against SQLite/CSV/JSON-backed DBs (`src/tools/text2sql_tool.py:22-40`, `:62-119`, `src/agent_architecture.py:2214-2232`).
- **MCP server integration**: supports loading tools from MCP stdio/HTTP servers via `langchain_mcp_adapters` (`src/tools/mcp_tools.py:11-16`, `:94-141`, `:221-263`).
- **Multiple LLM providers/models**: OpenAI, Anthropic, Groq, Google Vertex, etc., via custom client layer and LangChain chat classes (`llm_clients.py:18-22`, `:77-137`).
- **FastAPI + SSE streaming runtime**: API exposes `/deep-research` and streams events with `EventSourceResponse` (`routers/research.py:28-34`, `:300-381`).

If interpreted strictly as “external action tools,” browser automation is **not core runtime** here; Playwright/Puppeteer appear in examples only (`src/tools/examples/playwright_example.py`, `src/tools/examples/puppeteer_example.py`).

## 5. Notable Code Walkthrough

- `src/graph.py:284-415,5189-5276` - Defines the LangGraph workflow and the `multi_agents_network` node that invokes manager-led research; this is the top-level orchestration backbone.
- `src/agent_architecture.py:29-48,1002-1267,1516-1860` - Implements `MasterResearchAgent` planning/replanning, steering integration, and sequential/parallel subtask execution with semaphore-gated concurrency.
- `src/tools/search_tools.py:38-143,190-249` - Implements LangChain-compatible search tools that normalize outputs (sources/raw contents/domains) for downstream combination and citation.
- `src/tools/text2sql_tool.py:22-40,62-119,124-212` - Provides database ingestion and query execution path that enables data-centric research beyond plain web search.
- `routers/research.py:28-117,300-381` - Exposes runtime entrypoint (`/deep-research`) and SSE stream plumbing that turns the agent graph into a user-facing workflow service.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. The repo automates an end-to-end research workflow: request intake → query decomposition/planning → tool routing/search execution → iterative reflection/research loops → final report/answer generation, with optional steering and streaming status updates (`routers/research.py:28-117`, `src/graph.py:5189-5276`, `src/agent_architecture.py:1002-1270`). It is not primarily code generation or browser automation; it is a structured autonomous research pipeline orchestrating multiple agent roles and tools.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent separation (master/search/combiner/visualization) with explicit responsibilities (`src/agent_architecture.py:29-33`, `:2134-2140`, `:2451-2457`).
  - Strong control-flow explicitness via LangGraph conditional edges and loop routing (`src/graph.py:5225-5274`, `:3138-3196`).
  - Practical hybrid retrieval stack: web + academic/code/profile search + text2sql over user data (`src/tools/registry.py:45-71`, `src/agent_architecture.py:1581-1592`).
  - Supports human-in-the-loop steering (todo/constraints) without breaking automation (`src/prompts.py:148-205`, `src/agent_architecture.py:1151-1247`).
  - Streaming observability/events for long-running workflows (`routers/research.py:300-381`, `services/research.py:53-116`).

- **Limitations:**
  - Very large monolithic files (`src/graph.py`, `src/agent_architecture.py`) increase maintenance and verification burden.
  - Heavy prompt dependence and heuristic parsing can make behavior brittle across models/providers (`src/prompts.py:4-260`, `src/agent_architecture.py:240-260`).
  - Some robustness issues are acknowledged in comments/workarounds (e.g., state serialization workaround for `database_info`) (`src/graph.py:404-412`).
  - Tooling surface is broad, but production-hardening/guardrails around external tool failures appear uneven (many fallback branches and broad exception catches).
  - Parallel execution exists, but orchestration complexity (task mapping/skip logic/steering interactions) may be hard to reason about under failure (`src/agent_architecture.py:1728-1860`).

- **Research relevance:**
  - Useful case study of **graph-orchestrated hierarchical MAS** in a production-ish API backend.
  - Demonstrates integration of **LLM planning + tool ecosystems + iterative reflection loops** in one runtime.
  - Shows practical patterns for **human steering during autonomous loops** (todo-style dynamic constraints).
  - Provides evidence for hybrid data access in agents (web retrieval + structured DB querying) within one coordinated workflow.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
