---
repo_name: crewAIInc/crewAI-examples
url: "https://github.com/crewAIInc/crewAI-examples"
stars: 5895
forks: 2092
contributors_count: 63
last_commit_date: "2026-04-20T19:45:43+00:00"
primary_use_case: Workflow Automation
user_tier: Mainstream
total_score: 8
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T09:53:29.525677+00:00"
model: auto
duration_s: 67.9
clone_size_kb: 35717
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`crewAIInc/crewAI-examples` is a runnable collection of automation templates showing how to assemble LLM agents into end-to-end business workflows (trip planning, meeting task extraction, email triage, stock analysis, content generation). A user typically runs an example’s `main.py` (or a Flow kickoff), provides inputs (CLI prompts, files, or state), and gets structured outputs such as travel itineraries, extracted tasks, drafted emails, or investment recommendations. The repo is not a single app; it is a pattern library for composing agents, tasks, and tools around real integrations. Most examples focus on operational pipelines (analyze -> decide -> act), not chat UI. Several projects also show orchestration beyond plain crews (CrewAI Flows and a LangGraph integration).

## 2. Agent Framework & Architecture

The primary framework is **CrewAI**, confirmed by imports like `from crewai import Agent, Crew, Task, Process` and decorators in `crewai.project` (e.g., `crews/stock_analysis/src/stock_analysis/crew.py:1-3`, `flows/meeting_assistant_flow/src/meeting_assistant_flow/crews/meeting_assistant_crew/meeting_assistant_crew.py:1-3`). The repo also includes **CrewAI Flow** orchestration (`from crewai.flow.flow import Flow, listen, start` in `flows/meeting_assistant_flow/src/meeting_assistant_flow/main.py:6`) and at least one **LangGraph** integration (`from langgraph.graph import StateGraph` in `integrations/CrewAI-LangGraph/src/graph.py:4`).

High-level architecture is role-based multi-agent teams: agents are defined with role/goal/backstory and optional tools, tasks carry detailed prompts and expected outputs, and a crew executes them in sequence. In classic examples, “intelligence” mostly lives in task descriptions and agent role prompts (`crews/trip_planner/trip_tasks.py:7-88`, `crews/trip_planner/trip_agents.py:11-47`). In decorator-based examples, configuration is externalized to YAML (`agents.yaml` / `tasks.yaml`) and bound into typed crew classes (`flows/meeting_assistant_flow/.../meeting_assistant_crew.py:14-40`).

Some examples layer orchestration primitives above crews: Flow stages call a crew in one step then branch into side-effect actions (Trello/Slack/CSV), while the LangGraph integration embeds a CrewAI email-processing crew as a node in a state graph (`integrations/CrewAI-LangGraph/src/graph.py:15-29`).

## 3. Orchestration Pattern

Closest overall match: **sequential multi-agent workflow automation**, with secondary **graph/event-loop orchestration** in integrations.

Most crews execute ordered tasks across specialized agents:

```45:51:crews/trip_planner/main.py
    crew = Crew(
      agents=[
        city_selector_agent, local_expert_agent, travel_concierge_agent
      ],
      tasks=[identify_task, gather_task, plan_task],
      verbose=True
    )
```

Decorator-based crews explicitly set sequential process:

```35:40:flows/meeting_assistant_flow/src/meeting_assistant_flow/crews/meeting_assistant_crew/meeting_assistant_crew.py
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
```

Graph-style control exists in `integrations/CrewAI-LangGraph`, where state transitions decide whether to run the crew or wait:

```20:29:integrations/CrewAI-LangGraph/src/graph.py
		workflow.add_conditional_edges(
				"check_new_emails",
				nodes.new_emails,
				{
					"continue": 'draft_responses',
					"end": 'wait_next_run'
				}
		)
		workflow.add_edge('draft_responses', 'wait_next_run')
		workflow.add_edge('wait_next_run', 'check_new_emails')
```

## 4. Tools & External Integrations

- **Web search API (Serper)**: custom search tool posts to `https://google.serper.dev/search` with `SERPER_API_KEY` (`crews/trip_planner/tools/search_tools.py:15-22`).
- **Browserless + web parsing**: scraping via Browserless API and `unstructured` parsing (`crews/trip_planner/tools/browser_tools.py:15-21`).
- **Gmail toolkit**: email search/thread/draft through LangChain community Gmail tools (`integrations/CrewAI-LangGraph/src/nodes.py:4-14`, `integrations/CrewAI-LangGraph/src/crew/agents.py:35-37`, `integrations/CrewAI-LangGraph/src/crew/tools.py:16-23`).
- **Tavily search**: attached to email agents for action classification and drafting context (`integrations/CrewAI-LangGraph/src/crew/agents.py:3`, `:35-38`, `:51-53`).
- **Slack API**: posts flow notifications using `slack_sdk.WebClient` (`flows/meeting_assistant_flow/src/meeting_assistant_flow/utils/slack_helper.py:4-23`).
- **Trello REST API**: creates cards from extracted tasks (`flows/meeting_assistant_flow/src/meeting_assistant_flow/utils/trello_helper.py:21-40`).
- **SEC API + RAG over filings**: custom `RagTool` subclasses fetch 10-K/10-Q filings and semantic-search them (`crews/stock_analysis/src/stock_analysis/tools/sec_tools.py:24-41`, `:46-57`, `:105-120`).
- **Website tools from `crewai_tools`**: `ScrapeWebsiteTool`, `WebsiteSearchTool`, `TXTSearchTool` in stock-analysis crew wiring (`crews/stock_analysis/src/stock_analysis/crew.py:8`, `:27-33`, `:71-77`).
- **Multiple model backends**: examples use `ChatOpenAI(model="gpt-4")` and `Ollama(model="llama3.1")` (`flows/meeting_assistant_flow/.../meeting_assistant_crew.py:16`, `crews/stock_analysis/src/stock_analysis/crew.py:13-15`).

## 5. Notable Code Walkthrough

- `crews/trip_planner/main.py:17-54` - canonical three-agent CrewAI pipeline (city selector, local expert, concierge) wired into ordered tasks and kicked off with user inputs.
- `crews/trip_planner/trip_tasks.py:7-88` - shows where core reasoning guidance lives: rich task prompts, constraints, and expected outputs; this is the primary behavior-shaping layer.
- `flows/meeting_assistant_flow/src/meeting_assistant_flow/main.py:22-67` - demonstrates CrewAI Flow orchestration: transcript load -> crew extraction -> parallel post-processing actions (Trello, CSV, Slack).
- `flows/meeting_assistant_flow/src/meeting_assistant_flow/crews/meeting_assistant_crew/meeting_assistant_crew.py:10-40` - structured `@CrewBase` pattern with YAML-configured agents/tasks and typed Pydantic output.
- `integrations/CrewAI-LangGraph/src/graph.py:10-30` - hybrid architecture where LangGraph controls looping/branching and delegates one node to a multi-agent CrewAI email-processing crew.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** is accurate. Across examples, the repo repeatedly maps natural-language reasoning to operational steps: ingest business input (emails, meeting transcript, market question), run specialized agents in sequence, then trigger concrete actions (draft emails, create Trello cards, generate plans/reports). The `meeting_assistant_flow` is especially direct automation: extract tasks from transcript and immediately propagate artifacts to external systems (`flows/meeting_assistant_flow/src/meeting_assistant_flow/main.py:33-67`). Even when there is research/search, it is usually in service of a workflow output rather than standalone QA chat.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad set of real automation scenarios with executable code, not just conceptual docs.
  - Clear role/task decomposition makes coordination logic easy to inspect and reproduce.
  - Demonstrates framework interoperability (CrewAI crews inside Flow and LangGraph orchestration).
  - Rich tool integration patterns (APIs, SaaS actions, retrieval over external corpora).
  - Includes typed outputs and config-driven definitions in several modern examples.

- **Limitations:**
  - Repository quality is uneven across examples (older scripts vs newer `@CrewBase` projects).
  - Prompt-centric control dominates; limited explicit evaluation, guardrails, or reliability testing.
  - Sparse standardized observability/metrics for comparing agent performance across examples.
  - Some integrations rely heavily on external secrets/services, making reproducibility harder.
  - Limited evidence of robust failure handling/retries in many API-calling utility modules.

- **Research relevance:**
  - Useful evidence for **role-specialized cooperative agents** in practical workflow settings.
  - Demonstrates **hybrid orchestration** (agent teams embedded in graph/flow state machines).
  - Provides concrete cases of **LLM-agent tool use** with real-world APIs and side effects.
  - Suitable as a benchmark corpus for studying prompt/task decomposition strategies.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
