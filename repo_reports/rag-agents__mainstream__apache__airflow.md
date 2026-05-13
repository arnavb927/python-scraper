---
repo_name: apache/airflow
url: "https://github.com/apache/airflow"
stars: 45143
forks: 16905
contributors_count: 4287
last_commit_date: "2026-04-23T04:54:40+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-05-05T07:21:47.839778+00:00"
model: auto
duration_s: 123.9
clone_size_kb: 244894
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`apache/airflow` is a general workflow orchestration platform, and its LLM/agentic functionality lives in a dedicated provider package (`providers/common/ai`) rather than the core scheduler. A user runs DAGs that include operators like `LLMOperator`, `AgentOperator`, `LLMSQLQueryOperator`, and `LLMBranchOperator` to integrate model calls, tool use, and human review into normal Airflow tasks. In practice, this gives users reproducible, observable, retryable AI pipelines (e.g., generate SQL, execute queries, synthesize findings, request approval) instead of opaque single-shot chatbot interactions. The repo solves production orchestration concerns (scheduling, retries, auditing, approvals, durable execution) around AI-assisted workflow steps.

## 2. Agent Framework & Architecture

The actual agent framework is **PydanticAI** (not CrewAI/LangGraph). This is directly visible in imports such as `from pydantic_ai import Agent`, `from pydantic_ai.models import infer_model`, and toolset abstractions in `providers/common/ai/src/airflow/providers/common/ai/hooks/pydantic_ai.py:21-24` and `providers/common/ai/src/airflow/providers/common/ai/operators/agent.py:41-44`.

Architecture-wise, Airflow provides orchestration and task lifecycle, while the “intelligence” is encapsulated per task via PydanticAI agent instances created from Airflow connections. `AgentOperator` builds an agent with optional toolsets, runs `run_sync`, and can loop with human-in-the-loop regeneration (`providers/common/ai/src/airflow/providers/common/ai/operators/agent.py:201-217`, `227-312`). `LLMOperator` is a simpler single-call wrapper around the same hook (`providers/common/ai/src/airflow/providers/common/ai/operators/llm.py:125-139`).

The repo also demonstrates multi-step and multi-instance “agentic workflows” at DAG level (fan-out/fan-in, branching, approval) rather than a single centralized planner runtime. Example DAGs show decomposition into parallel LLM tasks plus synthesis (`providers/common/ai/src/airflow/providers/common/ai/example_dags/example_llm_survey_agentic.py:138-271`), which is coordinated by Airflow task graph semantics.

## 3. Orchestration Pattern

Closest match: **event-driven workflow orchestration (Airflow DAG)** with some **sequential and parallel stages**. It is not LangGraph-style internal state machine orchestration; control flow is managed by DAG dependencies and dynamic task mapping.

Control flow between “agents” is orchestrated at task level:

```190:197:providers/common/ai/src/airflow/providers/common/ai/example_dags/example_llm_survey_agentic.py
generate_sql = LLMSQLQueryOperator.partial(
    task_id="generate_sql",
    llm_conn_id=LLM_CONN_ID,
    datasource_config=survey_datasource,
    schema_context=SURVEY_SCHEMA,
    system_prompt=SQL_SYSTEM_PROMPT,
).expand(prompt=sub_questions)
```

```237:257:providers/common/ai/src/airflow/providers/common/ai/example_dags/example_llm_survey_agentic.py
collected = collect_results(run_query.output)

synthesize_answer = LLMOperator(
    task_id="synthesize_answer",
    llm_conn_id=LLM_CONN_ID,
    system_prompt=SYNTHESIS_SYSTEM_PROMPT,
    prompt="""\
...
Results: {{ ti.xcom_pull(task_ids='collect_results') }}""",
)
collected >> synthesize_answer
```

This shows fan-out (`expand`) and explicit dependency chaining (`>>`) across multiple LLM-backed tasks.

## 4. Tools & External Integrations

- **LLM providers via PydanticAI model/provider inference** (OpenAI, Anthropic, Groq, Mistral, Ollama, vLLM, plus Azure/Bedrock/Vertex hooks): `providers/common/ai/src/airflow/providers/common/ai/hooks/pydantic_ai.py:33-433`.
- **MCP servers** through an Airflow connection-backed toolset: `providers/common/ai/src/airflow/providers/common/ai/toolsets/mcp.py:30-96`; example wiring in `.../example_dags/example_mcp.py:30-73`.
- **SQL databases via Airflow `DbApiHook`** exposed as agent tools (`list_tables`, `get_schema`, `query`, `check_query`): `providers/common/ai/src/airflow/providers/common/ai/toolsets/sql.py:102-285`.
- **Generic Airflow hooks as callable tools** (method-introspection adapter): `providers/common/ai/src/airflow/providers/common/ai/toolsets/hook.py:53-137`.
- **Object/file analysis pipeline** (local/object storage files, optional multimodal attachments) used as LLM context: `providers/common/ai/src/airflow/providers/common/ai/operators/llm_file_analysis.py:36-166`.
- **DataFusion-backed schema introspection/execution path for SQL generation pipelines**: `providers/common/ai/src/airflow/providers/common/ai/operators/llm_sql.py:30-31`, `183-219`.
- **Human-in-the-loop review/approval** integrations via Airflow plugin and operators: `providers/common/ai/src/airflow/providers/common/ai/operators/agent.py:117-134`, `285-312`; workflow example with `ApprovalOperator` in `.../example_llm_survey_agentic.py:261-266`.

## 5. Notable Code Walkthrough

- `providers/common/ai/src/airflow/providers/common/ai/operators/agent.py:84-312`  
  Core “agent task” runtime: builds PydanticAI agent, injects toolsets, executes runs, supports durable step caching and iterative HITL regeneration. This is the main execution surface for agentic behavior in Airflow tasks.

- `providers/common/ai/src/airflow/providers/common/ai/hooks/pydantic_ai.py:33-208`  
  Abstraction layer mapping Airflow connections to concrete PydanticAI models/providers; centralizes credential/model resolution and agent creation. It is why DAG authors can switch providers without rewriting orchestration logic.

- `providers/common/ai/src/airflow/providers/common/ai/toolsets/sql.py:102-210`  
  Defines the SQL tool interface used by agents, including constrained tool schema and call routing. This file demonstrates how tool-augmented reasoning is integrated with enterprise data backends.

- `providers/common/ai/src/airflow/providers/common/ai/example_dags/example_llm_survey_agentic.py:138-271`  
  Representative “agentic workflow” DAG showing decomposition, parallel SQL generation, execution, aggregation, synthesis, and approval. It illustrates Airflow-native observability and retry behavior for AI pipelines.

- `providers/common/ai/src/airflow/providers/common/ai/operators/llm_branch.py:33-97`  
  Uses LLM structured output to choose downstream branches from DAG topology. This connects model decisions directly to orchestration control flow.

## 6. Use-Case Mapping

The upstream assignment `RAG + Agents` is **partially accurate but not primary** for this repo. Airflow’s AI code focuses more on **workflow automation of LLM/agent tasks** than canonical retrieval-augmented generation stacks (there is no central embedded retriever/vector-index architecture in core agent package). While there are integrations with vector-related providers elsewhere in the monorepo, the representative agentic implementation in `providers/common/ai` is about orchestrating tool-using LLM tasks, branching, approvals, and parallel pipelines. A better primary category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Production-grade orchestration primitives (retries, mapping, dependency graph, approvals) wrapped around LLM calls.
  - Clear separation between orchestration (Airflow DAG) and reasoning/tool execution (PydanticAI agent).
  - Strong integration surface: MCP, SQL, arbitrary hooks, cloud LLM providers, structured outputs.
  - Durable execution and replay support in `AgentOperator` reduces repeated model/tool costs on retries.
  - Good observability/auditability compared with monolithic agent loops (each step can be a task instance).

- **Limitations:**
  - Multi-agent coordination is mostly DAG-level composition, not deeply interactive agent-to-agent protocols.
  - No native LangGraph/CrewAI-style internal agent graph runtime in core architecture.
  - Heavy capability is concentrated in provider package; core Airflow remains general-purpose, so AI semantics are optional and fragmented.
  - Tool safety constraints (e.g., SQL table restrictions) rely partly on backend permissions and careful configuration.
  - Many examples are illustrative; production robustness depends on user DAG design and connection hygiene.

- **Research relevance:**
  - Evidence of “agentic workflows” implemented via classical workflow engines rather than bespoke MAS runtimes.
  - Useful case for studying human-in-the-loop governance integrated with LLM task execution.
  - Demonstrates practical bridging of enterprise tool ecosystems (DB hooks, MCP, cloud auth) into agent tool APIs.
  - Supports investigation of reliability patterns (durable replay, mapped retries, auditable intermediate artifacts) in LLM operations.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
