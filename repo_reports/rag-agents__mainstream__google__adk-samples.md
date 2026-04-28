---
repo_name: google/adk-samples
url: "https://github.com/google/adk-samples"
stars: 8938
forks: 2415
contributors_count: 119
last_commit_date: "2026-04-21T00:23:21+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T11:54:23.612767+00:00"
model: auto
duration_s: 104.4
clone_size_kb: 508193
uses_mas: yes
final_use_case: Workflow Automation
---
I have enough concrete evidence now: ADK is the primary framework, with multiple runtime orchestration patterns (sequential workflows, graph-style `WorkflowAgent` edges, and manager/sub-agent delegation), plus integrations like Vertex RAG, BigQuery toolsets, Calendar MCP, and Gmail via LangChain. I’ll now synthesize this into the exact 8-section Markdown report format you specified.## 1. Overview

`google/adk-samples` is a large, multi-language repository of runnable agent examples built on Google’s Agent Development Kit (ADK), with Python containing the broadest set of end-to-end systems. A user typically enters a specific sample directory (for example `python/agents/RAG` or `python/agents/hierarchical-workflow-automation`) and runs it via `adk run <agent>` or `adk web` to interact through CLI/UI. What they get is not just chat completion, but orchestrated agent behavior: delegated sub-agents, explicit workflow nodes, and tool-using execution over external services (RAG corpora, BigQuery, Calendar, Gmail). The repository’s practical value is as a cookbook for agentic application patterns rather than a single product.

## 2. Agent Framework & Architecture

The framework actually used is **Google ADK** (not CrewAI). This is directly evidenced by imports like `from google.adk.agents import Agent`, `SequentialAgent`, `WorkflowAgent`, `LlmAgent`, and ADK tool modules such as `google.adk.tools.retrieval.vertex_ai_rag_retrieval` and `google.adk.tools.bigquery` (e.g., `python/agents/workflows-sequential/agent.py:4-7`, `python/agents/RAG/rag/agent.py:20-23`, `python/agents/hierarchical-workflow-automation/cookie_scheduler_agent/bigquery_utils/bigquery_tools.py:10-12`). LangChain appears in selected integrations (not orchestration core), such as Gmail toolkit wiring in the cookie scheduler sample (`python/agents/hierarchical-workflow-automation/cookie_scheduler_agent/agent.py:71-79`).

Architecture is sample-driven and heterogeneous: each agent folder defines a `root_agent`, then composes sub-agents or workflow nodes based on use case. In manager/sub-agent systems, intelligence is distributed via role-specific instructions on child agents and delegated execution (`python/agents/travel-concierge/travel_concierge/agent.py:38-51`). In workflow-centric systems, intelligence is embedded in graph edges and node sequencing (`python/agents/workflow-concurrent_research_writer/agent.py:36-46`, `71-91`, `93-101`). In RAG samples, intelligence is primarily prompt+tool policy in one ADK agent, where the model decides when to call retrieval (`python/agents/RAG/rag/prompts.py:22-64`, `python/agents/RAG/rag/agent.py:64-70`).

## 3. Orchestration Pattern

Closest match: **other (hybrid)**, combining **sequential**, **hierarchical manager-worker**, and **graph/state-machine** patterns depending on sample.

Control flow is explicit in ADK workflow edges for graph-style routing:

```35:41:python/agents/workflows-sequential/agent.py
root_agent = WorkflowAgent(
    name="root_agent",
    edges=[
        (START, city_generator_agent, lookup_time_function, city_report_agent)
    ],
)
```

And hierarchical delegation appears in manager agents that hand work to sub-agents:

```803:831:python/agents/hierarchical-workflow-automation/cookie_scheduler_agent/agent.py
delivery_workflow_agent = SequentialAgent(
    name="delivery_workflow_agent",
    description="Manages the entire cookie delivery process from order to confirmation.",
    sub_agents=[store_database_agent, calendar_agent, email_agent],
)

root_agent = Agent(
    ...
    sub_agents=[delivery_workflow_agent],
)
```

So this repo is not one orchestration model; it is a pattern library showing multiple runtime coordination strategies.

## 4. Tools & External Integrations

- **Vertex AI RAG Engine retrieval** via ADK `VertexAiRagRetrieval`, attached as a tool to the RAG agent (`python/agents/RAG/rag/agent.py:21-23`, `46-63`).
- **RAG corpus provisioning pipeline** (download PDF, create corpus, upload file, persist corpus ID) in Vertex AI (`python/agents/RAG/rag/shared_libraries/prepare_corpus_and_data.py:62-83`, `100-111`, `127-131`).
- **BigQuery ADK first-party toolset** (`BigQueryToolset`, `execute_sql` pattern) for order queries and updates (`python/agents/hierarchical-workflow-automation/cookie_scheduler_agent/bigquery_utils/bigquery_tools.py:10-12`, `21-43`, `64-79`, `103-117`).
- **Google Calendar via MCP server** exposing tools (`get_events`, `create_event`, `check_availability`) and used by agent logic (`python/agents/hierarchical-workflow-automation/cookie_scheduler_agent/mcp_servers/calendar/calendar_mcp_server.py:356-438`, `441-477`; called in `.../agent.py:240-245`, `388-395`).
- **Gmail via LangChain toolkit wrapper** for sending confirmation emails in workflow (`python/agents/hierarchical-workflow-automation/cookie_scheduler_agent/agent.py:71-79`, `487-506`).
- **Google Search grounding tool** as ADK tool in travel concierge (`python/agents/travel-concierge/travel_concierge/tools/search.py:19-33`).
- **Observability/Tracing** through OpenInference/Arize instrumentation (`python/agents/travel-concierge/travel_concierge/agent.py:20`, `30`, `34`; `python/agents/RAG/rag/agent.py:24`, `27`, `38`).

## 5. Notable Code Walkthrough

- `python/agents/hierarchical-workflow-automation/cookie_scheduler_agent/agent.py:665-831`  
  Defines a full multi-agent business workflow: database agent, calendar agent, email agent (with haiku sub-agent), then composes them in a `SequentialAgent` under a root manager.
- `python/agents/workflow-concurrent_research_writer/agent.py:36-101`  
  Demonstrates ADK graph orchestration with parallel worker fan-out (`ParallelWorker`), branching routes, and chained workflow phases (research → publishing).
- `python/agents/RAG/rag/agent.py:40-70`  
  Minimal but clear RAG implementation: conditionally wires `VertexAiRagRetrieval` based on environment corpus config and exposes it to the ADK root agent.
- `python/agents/RAG/rag/shared_libraries/prepare_corpus_and_data.py:62-83,144-171`  
  Operational setup layer for RAG: creates or reuses corpus, uploads documents, and updates `.env` with corpus resource names.
- `python/agents/hierarchical-workflow-automation/cookie_scheduler_agent/mcp_servers/calendar/calendar_mcp_server.py:50-121,356-477`  
  Implements a real MCP server with OAuth-authenticated Calendar operations and tool-call handlers, showing how external services are exposed to agent systems.

## 6. Use-Case Mapping

Although the assigned label is `RAG + Agents`, the repository as a whole is broader: it is a **general ADK sample suite** with many domains and orchestration demos. The code includes RAG-specific implementations (notably `python/agents/RAG`), but many flagship examples are workflow automation pipelines coordinating multiple specialized agents plus business tools (BigQuery, Calendar, Gmail), especially `hierarchical-workflow-automation`. Therefore, for repository-level classification, **Workflow Automation** is a better primary category than RAG-only. RAG is clearly present, but not dominant across the full codebase’s architecture patterns.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Shows multiple real orchestration forms (sequential, graph routing, hierarchical delegation) in runnable code.
  - Integrates real external systems (Vertex RAG, BigQuery, Calendar MCP, Gmail) rather than toy in-memory tools.
  - Keeps orchestration explicit and inspectable via ADK primitives (`WorkflowAgent` edges, `SequentialAgent`, `sub_agents`).
  - Includes fallback behavior to dummy data, making examples runnable even without full cloud setup.
  - Covers end-to-end lifecycle patterns (local run, evaluation, deployment scaffolding).

- **Limitations:**
  - Repository is a collection of disparate samples, so architecture is inconsistent and hard to compare systematically.
  - Quality/maturity varies; some samples are heavily instructional and not production-hardened.
  - External dependency burden is high (cloud credentials, OAuth setup, API quotas), limiting reproducibility.
  - Several tool paths rely on prompt discipline and implicit state passing, which can be brittle.
  - Limited unified benchmark methodology across all multi-agent examples.

- **Research relevance:**
  - Useful evidence for practical **tool-augmented multi-agent orchestration** patterns in contemporary LLM systems.
  - Demonstrates real-world **agent-to-service coupling** (DB, calendar, email, retrieval) beyond pure text planning.
  - Provides examples of **hybrid control topologies** (manager-worker + graph workflows) within one framework.
  - Supports study of tradeoffs between single-agent RAG and multi-agent workflow automation in the same ecosystem.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
