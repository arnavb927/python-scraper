---
repo_name: aws-samples/sample-agentic-frameworks-on-aws
url: "https://github.com/aws-samples/sample-agentic-frameworks-on-aws"
stars: 254
forks: 91
contributors_count: 32
last_commit_date: "2026-04-14T20:49:23+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 4
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T15:44:27.386353+00:00"
model: auto
duration_s: 169.0
clone_size_kb: 242079
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a collection of runnable AWS-focused agentic AI samples rather than a single application, with subprojects built around different frameworks (LangGraph/LangChain, CrewAI, Strands, MCP, etc.). In practice, users run specific examples such as `langchain/customer_support/main.py` for automated Jira ticket triage/response, `crewai/aws-security-auditor-crew/.../crew.py` for security audit report generation, or `strands-agents/waf-logs-in-clickhouse-with-mcp/main.py` for natural-language log analytics over ClickHouse. The outputs are task artifacts (updated Jira fields, generated markdown reports, conversational support responses, SQL-backed analytics answers), not just chat replies. The repo solves the “how do I build production-oriented agent workflows on AWS” problem by showing orchestration, tool use, memory, and service integrations in code.

## 2. Agent Framework & Architecture

Framework usage is **actually multi-framework** in code:  
- **LangGraph/LangChain** (`langchain/customer_support/cs_cust_support_flow.py:10-15`, `langchain/shopping-agent/agents/agent.py:7-13`, `langchain/shopping-agent/agents/subagents.py:4-5`)  
- **CrewAI** (`crewai/aws-security-auditor-crew/src/aws_infrastructure_security_audit_and_reporting/crew.py:1-2`)  
- **Strands Agents** (`strands-agents/waf-logs-in-clickhouse-with-mcp/main.py:5-8`, `strands-agents/support-agent/app.py:3-5`)

Architecture differs per sample, but the recurring pattern is: an orchestrator (graph/supervisor/crew process) routes work to specialized agent roles plus tools. For example, `langchain/customer_support` encodes workflow intelligence in LangGraph nodes and conditional edges (`cs_cust_support_flow.py:512-539`), while `langchain/shopping-agent` has a supervisor router that dispatches to two subagents (`agent.py:44-95`, `agent.py:348-356`, `subagents.py:21-41`).

The “intelligence” is distributed across (a) role prompts/configs (`agents.yaml`, system prompts in `cs_cust_support_flow.py:580-590`, `strands-agents/support-agent/app.py:45-67`), (b) routing/planning logic (conditional functions like `decide_ticket_flow_condition` and `route_after_supervisor`), and (c) tool ecosystems (DB lookups, OpenSearch retrieval, Jira updates, MCP-exposed services, web tools).

## 3. Orchestration Pattern

Closest overall match: **graph orchestration (LangGraph-style state machine)**, with some manager-worker elements in specific demos.

In `langchain/customer_support`, control flow is explicitly graph-driven with conditional branches:

```544:539:langchain/customer_support/cs_cust_support_flow.py
graph_builder.add_edge(START, "Determine Ticket Category")
graph_builder.add_conditional_edges("Assign Ticket Category in JIRA", self.decide_ticket_flow_condition)
graph_builder.add_conditional_edges("Find Order Details", self.order_query_decision, ["Generate Response", "tools"])
graph_builder.add_edge("tools", "Generate Response")
graph_builder.add_edge("Update Response in JIRA", END)
```

In `langchain/shopping-agent`, a supervisor node routes to specialized subagent nodes:

```347:355:langchain/shopping-agent/agents/agent.py
workflow_builder.add_conditional_edges(
    "supervisor",
    route_after_supervisor,
    {
        "opensearch_agent": "opensearch_agent",
        "invoice_agent": "invoice_agent",
        "FINISH": "create_memory"
    }
)
```

This is not a peer-to-peer swarm; routing is centrally controlled by graph edges/router functions.

## 4. Tools & External Integrations

- **Amazon Bedrock LLMs + Guardrails**: `ChatBedrockConverse` init plus guardrail creation/deletion in `langchain/customer_support/cs_bedrock.py:25-52` and `:55-177`; Bedrock model use in Strands agents (`strands-agents/support-agent/app.py:40-43`, `waf-logs.../main.py:189-194`).
- **Jira API integration**: ticket fetch/update and field writes via `JiraSM` in `langchain/customer_support/cs_cust_support_flow.py:119-123`, `:560-577`, `:478-483`.
- **SQLite operational data**: transaction/order/refund lookup in `langchain/customer_support/cs_db.py:26-46` and query calls in `cs_cust_support_flow.py:237-247`, `:391-399`.
- **OpenSearch vector search + agentic memory**: neural product retrieval tools (`langchain/shopping-agent/agents/tools.py:27-43`, `:164-204`), OpenSearch client/auth setup (`opensearch_client.py:18-100`), and memory container CRUD/search (`opensearch_memory_client.py:46-130`, `:132-241`, `:243-308`).
- **MCP integration**: Strands agent loads tools from MCP server and mixes them with local tools in `strands-agents/waf-logs-in-clickhouse-with-mcp/main.py:178-188`.
- **Web search/scraping tools**: CrewAI security analyst uses `SerperDevTool` and `ScrapeWebsiteTool` in `crewai/.../crew.py:32-33`.
- **RAG/KB retrieval**: Strands support agent includes `retrieve` tool with Bedrock knowledge base id wiring in `strands-agents/support-agent/app.py:35-37`, `:72-74`.

## 5. Notable Code Walkthrough

- `langchain/customer_support/cs_cust_support_flow.py:25-550` - Core LangGraph workflow for customer support: state schema, ticket categorization, conditional routing, tool-calling path, response generation, and Jira writeback.
- `langchain/shopping-agent/agents/agent.py:44-367` - Multi-agent supervisor graph with account verification, human interrupt support, memory load/create stages, and routing into invoice vs product-search subagents.
- `langchain/shopping-agent/agents/subagents.py:21-41` - Defines two specialized LangChain subagents (`invoice_subagent`, `opensearch_subagent`) used by the supervisor graph.
- `langchain/shopping-agent/agents/tools.py:10-424` - Concrete tool surface (OpenSearch neural retrieval/recommendation + SQL invoice lookup), showing where agent capabilities are grounded.
- `crewai/aws-security-auditor-crew/src/aws_infrastructure_security_audit_and_reporting/crew.py:20-73` - Clear CrewAI multi-role setup (mapper, analyst, report writer) with sequential task process and AWS-backed LLM configuration.

## 6. Use-Case Mapping

The assigned label **RAG + Agents** is partially correct but incomplete. This repo absolutely contains RAG-like agent patterns (e.g., OpenSearch neural retrieval and memory-backed recommendations in `shopping-agent`, KB retrieval tool usage in `strands-agents/support-agent`), yet many flagship examples are broader **multi-step business workflow automation** (security audit pipelines, support-ticket lifecycle orchestration, log-analysis workflows). Based on actual runtime code, the best single bucket is **Workflow Automation**, with RAG as a recurring technique inside multiple workflows rather than the sole purpose.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Demonstrates real multi-agent coordination patterns (graph routing, sequential crews, supervisor-subagent).
- Integrates with realistic external systems (Jira, OpenSearch, Bedrock guardrails, MCP, SQL/ClickHouse).
- Shows production-ish concerns: safety guardrails, memory/persistence, conditional control flow, human interrupt points.
- Provides multiple framework implementations in one repo, useful for comparative study.
- Includes specialized role/task decomposition with explicit responsibilities and handoffs.

- **Limitations:**
- Monorepo heterogeneity means uneven quality and architecture consistency across subprojects.
- Several examples are notebook-centric or demo-oriented, reducing reproducibility for strict benchmarking.
- Hard-coded model/service assumptions in places (region/model IDs/env dependencies) can hinder portability.
- Limited unified evaluation harness across examples; performance/safety claims are mostly implementation-level.
- Some workflows are deterministic pipelines with LLM steps, but not all are deeply adaptive multi-agent systems.

- **Research relevance:**
- Good evidence of **applied MAS orchestration patterns** (graph routing vs sequential crews) in practical enterprise tasks.
- Useful for studying **tool-augmented LLM agents** interacting with heterogeneous backends (search, DB, APIs, MCP).
- Supports analysis of **memory-augmented personalization** via OpenSearch agentic memory in a live agent flow.
- Illustrates AWS-centric deployment and safety integration patterns for agentic systems in operational contexts.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
