---
repo_name: 1Panel-dev/MaxKB
url: "https://github.com/1Panel-dev/MaxKB"
stars: 20797
forks: 2791
contributors_count: 82
last_commit_date: "2026-04-23T02:46:22+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 7
architecture_labels: [LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T10:45:52.495230+00:00"
model: auto
duration_s: 96.4
clone_size_kb: 88633
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`MaxKB` is a Django-based platform for building and running LLM-powered “applications” that can be either simple RAG chat pipelines or graph-defined workflows with many node types. In practice, users run the web service (`main.py` starts Django/web/celery services) and then configure applications in the UI; each chat request is routed through either a fixed pipeline or a workflow executor (`apps/chat/serializers/chat.py:337-470`). The output is a streamed or blocking chat response, plus persisted execution details, token usage, and node-level runtime traces. The system is not just a UI wrapper: it contains a real runtime for graph orchestration, tool/MCP invocation, and knowledge retrieval.

## 2. Agent Framework & Architecture

This repo uses **LangChain + LangGraph-adjacent tooling + custom orchestration**, not CrewAI/AutoGen. Evidence: `langchain`, `langgraph`, and `deepagents` are first-class dependencies (`pyproject.toml:24-37`), and runtime code imports `create_deep_agent`, `MemorySaver`, `MultiServerMCPClient`, and LangChain message/tool classes (`apps/application/flow/tools.py:37-45`).

Architecture is split into two execution paths:
1) **Simple chat pipeline** (`BaseSearchDatasetStep -> BaseGenerateHumanMessageStep -> BaseChatStep`) assembled in `PipelineManage` (`apps/chat/serializers/chat.py:347-357`, `apps/application/chat_pipeline/pipeline_manage.py:18-38`).
2) **Workflow engine** for graph apps: `WorkflowManage` executes node DAGs built from JSON workflow definitions (`apps/chat/serializers/chat.py:416-439`, `apps/application/flow/common.py:107-194`).

The “intelligence” lives in node implementations (especially `ai-chat-node`) plus prompt templating and tool orchestration. `BaseChatNode` builds messages/prompt context, resolves model settings, optionally activates MCP/tools, and invokes/streams model output (`apps/application/flow/step_node/ai_chat_step_node/impl/base_chat_node.py:154-239`). When tools/MCP are enabled, control moves into `mcp_response_generator`, which runs a deep agent loop with tool-call streaming and parsing logic (`apps/application/flow/tools.py:408-441`, `421-433`, `504-717`).

## 3. Orchestration Pattern

Closest match: **graph (state-machine/DAG) orchestration with hierarchical subcalls**.

The core workflow control flow is graph-based: after each node result, next runnable nodes are selected from edges and executed sequentially or in parallel threads (`apps/application/flow/workflow_manage.py:645-703`, `355-377`).

```355:377:apps/application/flow/workflow_manage.py
if current_node is None:
    start_node = self.get_start_node()
    current_node = get_node(start_node.type, self.flow.workflow_mode)(start_node, self.params, self)
...
node_list = self.get_next_node_list(current_node, result)
if len(node_list) == 1:
    self.run_chain_manage(node_list[0], None, language)
elif len(node_list) > 1:
    result_list = [{'node': node, 'future': executor.submit(self.run_chain_manage, node, None, language)} for node in sorted_node_run_list]
```

It also supports hierarchical manager-worker behavior via nested app/tool workflows. `application-node` calls another published application through chat serializers (effectively agent-as-subagent) and streams results back into parent context (`apps/application/flow/step_node/application_node/impl/base_application_node.py:184-255`).

```184:199:apps/application/flow/step_node/application_node/impl/base_application_node.py
def execute(self, application_id, message, chat_id, chat_record_id, stream, re_chat, ...):
    from chat.serializers.chat import ChatSerializers
    if application_id == self.workflow_manage.get_body().get('application_id'):
        raise Exception(_("The sub application cannot use the current node"))
    current_chat_id = string_to_uuid(chat_id + application_id)
    Chat.objects.get_or_create(id=current_chat_id, defaults={...})
```

## 4. Tools & External Integrations

- **LLM providers (OpenAI/Anthropic/Gemini/DeepSeek/etc.)**: model abstraction and provider adapters via `models_provider`; selected at runtime in nodes (`apps/application/flow/step_node/ai_chat_step_node/impl/base_chat_node.py:193-195`).
- **MCP servers**: MCP configs from custom JSON or stored tool definitions, then loaded via `MultiServerMCPClient` (`apps/application/flow/step_node/ai_chat_step_node/impl/base_chat_node.py:256-265`, `apps/application/flow/tools.py:403-415`).
- **Deep agent runtime + LangGraph memory**: `create_deep_agent(..., checkpointer=MemorySaver())` for iterative tool-using agent loops (`apps/application/flow/tools.py:421-433`, `412`).
- **Sandboxed shell/file backend**: deep agent runs with `SandboxShellBackend(root_dir=temp_dir, virtual_mode=True)` (`apps/application/flow/tools.py:423`).
- **Internal workflow tools exposed as LangChain `StructuredTool`**: workflow tools are dynamically generated and callable by agent (`apps/application/flow/tools.py:1038-1064`).
- **Agent-to-agent/application calls**: applications can be mounted as callable tools (MCP config built from app API key) (`apps/application/flow/step_node/ai_chat_step_node/impl/base_chat_node.py:285-311`).
- **RAG/vector retrieval**: embedding search against PG vector storage (`apps/application/flow/step_node/search_knowledge_node/impl/base_search_knowledge_node.py:105-117`, `apps/knowledge/vector/pg_vector.py:101-120`).
- **MCP gateway endpoint**: repo exposes tools over MCP protocol (`apps/chat/mcp/tools.py:21-48`, `66-105`).

## 5. Notable Code Walkthrough

- `apps/chat/serializers/chat.py:392-470` - Main runtime entry for workflow applications; builds `WorkflowManage`, injects context (history, user, files), and executes streaming/blocking chat.
- `apps/application/flow/workflow_manage.py:351-703` - Core DAG executor: runs nodes, handles branching/conditions, parallel fan-out, and computes next runnable nodes.
- `apps/application/flow/step_node/ai_chat_step_node/impl/base_chat_node.py:154-359` - LLM node implementation; prompt/message assembly, model invocation, tool/MCP wiring, and agent tool execution handoff.
- `apps/application/flow/tools.py:408-441` and `504-717` - Deep-agent + MCP streaming loop; aggregates tool call fragments across chunk formats and emits tool-rendered outputs robustly.
- `apps/application/flow/step_node/search_knowledge_node/impl/base_search_knowledge_node.py:76-137` - RAG retrieval node; embeds query, performs vector search, and writes ranked paragraph evidence into workflow context.

## 6. Use-Case Mapping

This repo concretely implements **RAG + Agents**, but the dominant runtime style is **workflow automation of agentic steps**. RAG is explicit in `search-knowledge-node` (embedding query + vector retrieval + evidence context) (`apps/application/flow/step_node/search_knowledge_node/impl/base_search_knowledge_node.py:105-134`). Agent behavior appears in `ai-chat-node` when MCP/tools are enabled and executed by `deepagents` (`apps/application/flow/step_node/ai_chat_step_node/impl/base_chat_node.py:333-357`, `apps/application/flow/tools.py:421-441`). Multi-agent flavor exists through sub-application invocation and application-as-tool patterns (`apps/application/flow/step_node/application_node/impl/base_application_node.py:184-255`, `apps/application/flow/step_node/ai_chat_step_node/impl/base_chat_node.py:285-311`), but orchestration is centrally managed by a workflow graph engine.

Given the allowed output taxonomy, the best fit is **Workflow Automation** (with strong RAG+agent capabilities embedded inside that automation framework).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Strong production-oriented orchestration engine with branching, dependency checks, and parallel fan-out (`workflow_manage.py`).
- Unified runtime that combines classic RAG retrieval nodes and tool-using LLM agent nodes in one graph.
- Rich integration model: MCP, custom tools, nested tool workflows, and application-as-tool.
- Robust streaming/tool-call handling across inconsistent provider chunk formats (`tools.py` tool fragment reconciliation).
- Fine-grained execution observability persisted per node (tokens, run time, errors, intermediate outputs).

- **Limitations:**
- Orchestration is mostly thread-based custom logic; no explicit formal state graph guarantees beyond code conventions.
- Agent behavior is tightly coupled to platform internals (Django models, serializers), reducing portability/reproducibility.
- Complex monolithic files (`tools.py`, `chat.py`) increase maintenance and reasoning overhead.
- Limited explicit safeguards/verification for emergent multi-agent coordination quality (focus is operational, not deliberative reliability).
- Heavy dynamic configuration makes behavior highly deployment-dependent (tool auth, MCP configs, model providers).

- **Research relevance:**
- Evidence of **hybrid agent systems** combining DAG workflow control with tool-using LLM loops in production.
- Useful case study for **agent interoperability via MCP** and app-as-tool composition.
- Demonstrates practical challenges of **streamed tool-call assembly** across heterogeneous model providers.
- Illustrates enterprise pattern of integrating RAG, tools, and nested agents under centralized orchestration.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
