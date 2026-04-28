---
repo_name: dataelement/bisheng
url: "https://github.com/dataelement/bisheng"
stars: 11324
forks: 1845
contributors_count: 61
last_commit_date: "2026-03-27T11:32:12+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [LangChain, CrewAI]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-04-27T11:09:56.577336+00:00"
model: auto
duration_s: 121.3
clone_size_kb: 168363
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`bisheng` is a FastAPI-based enterprise AI platform backend that lets users build and run LLM applications as visual workflows, assistants, and tool-augmented chats. The runtime compiles user-defined node/edge graphs into executable pipelines, then serves them through API/WebSocket chat endpoints (`src/backend/bisheng/main.py`, `src/backend/bisheng/api/services/workflow.py`). In practice, a user configures a workflow/assistant in the product UI, then invokes it via chat/completions or workflow execution endpoints and receives streamed answers, tool traces, and optional human-interrupt steps. The system also supports configurable agent modes (ReAct/function-calling), knowledge retrieval, and optional AutoGen multi-role conversations.

## 2. Agent Framework & Architecture

Framework usage is **mixed** and confirmed in code:  
- **LangGraph** (`StateGraph`, `create_react_agent`) is used for both workflow graph execution and function-calling agent construction (`src/backend/bisheng/workflow/graph/graph_engine.py`, `src/backend/bisheng/api/services/assistant_agent.py`).  
- **LangChain** is heavily used for models, tools, chains, memory, and agent executors throughout the backend (`src/backend/bisheng/workflow/nodes/agent/agent.py`, `src/backend/bisheng/interface/initialize/loading.py`).  
- **AutoGen** is explicitly implemented for multi-role/group-chat agents (`src/backend/bisheng_langchain/chains/autogen/auto_gen.py`, `src/backend/bisheng_langchain/autogen_role/groupchat_manager.py`).  
- No evidence of CrewAI runtime usage in core execution paths.

High-level architecture has two major execution planes. First, a **workflow engine** compiles node graphs into a LangGraph state machine; nodes include LLM, Agent, Tool, RAG, Input/Output, etc., and can pause for user input before resuming (`src/backend/bisheng/workflow/graph/graph_engine.py`). Second, an **assistant runtime** initializes LLM + tools + linked flows/knowledge, then runs either a ConfigurableAssistant ReAct path or LangGraph `create_react_agent` function-calling path (`src/backend/bisheng/api/services/assistant_agent.py`).

The “intelligence” lives mainly in node prompts, assistant prompts, tool selection/loading, and graph routing logic. For MAS-specific behavior, AutoGen roles (user proxy, assistant, manager, custom role) are separately modeled and can be instantiated through the dynamic component loader (`src/backend/bisheng/interface/autogenRole/base.py`, `src/backend/bisheng/interface/initialize/loading.py`).

## 3. Orchestration Pattern

Closest match: **Graph orchestration (LangGraph-style state machine) with optional hierarchical multi-agent subgroup (AutoGen manager + agents)**.

Control flow for workflow graph is explicit: build nodes/edges, add conditional edges, compile, stream execution, and interrupt on input nodes.

```277:283:src/backend/bisheng/workflow/graph/graph_engine.py
# compile langgraph
self.graph = self.graph_builder.compile(checkpointer=MemorySaver(),
                                        interrupt_before=interrupt_nodes)
self.graph_config['recursion_limit'] = max(
    (len(nodes) - len(end_nodes) - 1) * self.max_steps, 1) + len(end_nodes) + 1
```

```303:309:src/backend/bisheng/workflow/graph/graph_engine.py
async def _arun(self, input_data: Any):
    try:
        self.status = WorkflowStatus.RUNNING.value
        async for _ in self.graph.astream(input_data, config=self.graph_config):
            pass
        self.judge_status()
```

MAS/group-chat orchestration is manager-worker style via AutoGen `GroupChatManager` controlling multiple agents:

```34:38:src/backend/bisheng_langchain/autogen_role/groupchat_manager.py
if not any(isinstance(agent, AutoGenUser) for agent in agents):
    raise Exception('chat_manager must contains AutoGenUser')

groupchat = GroupChat(agents=agents, messages=[], max_round=max_round)
```

## 4. Tools & External Integrations

- **Built-in/preset/API/MCP tool loading** via unified executor (`src/backend/bisheng/tool/domain/services/executor.py`).
- **MCP servers/tools** supported via `ClientManager.sync_connect_mcp_from_json` and wrapped as LangChain `StructuredTool` (`src/backend/bisheng/tool/domain/services/executor.py`, `src/backend/bisheng/mcp_manage/langchain/tool.py`).
- **Web/search tools**: Bing search and generic web search providers (`src/backend/bisheng_langchain/gpts/load_tools.py`).
- **Code execution / terminal-like execution**: native code interpreter tool with local or E2B executors (`src/backend/bisheng_langchain/gpts/load_tools.py`, `src/backend/bisheng_langchain/gpts/tools/code_interpreter/tool.py`).
- **Local filesystem tools**: list/read/search/add/replace file operations through `LocalFileTool` mapping (`src/backend/bisheng_langchain/gpts/load_tools.py`).
- **RAG pipeline integrations**: knowledge tools backed by Milvus + Elasticsearch retrievers (`src/backend/bisheng/tool/domain/services/executor.py`, `src/backend/bisheng/workflow/nodes/agent/agent.py`).
- **SQL agent/database access** via SQL tool wrappers (`src/backend/bisheng_langchain/gpts/load_tools.py`, `src/backend/bisheng/workflow/nodes/agent/agent.py`).
- **Image generation** via DALL-E wrappers and Azure/OpenAI-compatible configs (`src/backend/bisheng_langchain/gpts/load_tools.py`).
- **OpenAPI/custom HTTP tools** through API tool registry and OpenAPI schema parsing (`src/backend/bisheng/tool/domain/services/executor.py`, `src/backend/bisheng_langchain/gpts/tools/api_tools/*`).

## 5. Notable Code Walkthrough

- `src/backend/bisheng/workflow/graph/graph_engine.py:27-388`  
  Core orchestrator that translates user workflow JSON into a LangGraph executable graph, manages fan-in/fan-out, conditional routing, interruption points, and run lifecycle/status.

- `src/backend/bisheng/workflow/nodes/agent/agent.py:50-405`  
  Agent node implementation that assembles prompts, chat history, tools, knowledge retrievers, optional SQL agent tooling, then executes either ReAct or function-calling mode.

- `src/backend/bisheng/api/services/assistant_agent.py:34-421`  
  Assistant runtime used by public chat APIs: initializes model/toolset (including flow-as-tool), builds agent executor, handles streaming/non-streaming, and tracks tool/trace behavior.

- `src/backend/bisheng/tool/domain/services/executor.py:63-305`  
  Central adapter that instantiates preset/API/MCP/knowledge tools and wraps them with telemetry + LangChain `BaseTool` execution semantics.

- `src/backend/bisheng_langchain/chains/autogen/auto_gen.py:15-99`  
  Multi-agent chain wrapper around AutoGen conversations, including initiate chat, async flow, intermediate-step capture, and stop/reset hooks.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially true. The repo does include browser/search-like and terminal-like capabilities (web search tools, code interpreter/execution), but these are optional tools inside a broader platform. The dominant behavior is **orchestrating business/LLM workflows** with configurable nodes, tool calls, knowledge retrieval, and human-in-the-loop interrupts.  

A better primary label is **Workflow Automation** (with strong secondary support for RAG + Agents).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Combines LangGraph graph execution with tool-rich LangChain agents in one production backend.
  - Supports both single-agent and explicit multi-agent (AutoGen group chat) paradigms.
  - Strong pluggability: dynamic node/type loading and heterogeneous tool sources (preset/API/MCP/knowledge).
  - Built-in interruption/resume semantics for human-in-the-loop workflows.
  - Telemetry hooks integrated at tool and app-process levels.

- **Limitations:**
  - Architecture is broad/complex, making end-to-end agent behavior harder to reason about formally.
  - Multiple overlapping execution frameworks (LangChain agents, LangGraph, AutoGen) increase maintenance surface.
  - Some Browser/Terminal capabilities are tool-level, not a dedicated autonomous browser/terminal agent loop.
  - Several code paths rely on dynamic config/DB state, reducing reproducibility from code alone.
  - Prompt/orchestration behavior is distributed across many node/service files, with limited centralized policy layer.

- **Research relevance:**
  - Evidence of hybrid orchestration: graph workflows plus agentic tool-use in enterprise settings.
  - Useful case for studying interoperability between LangGraph, LangChain, and AutoGen in one system.
  - Demonstrates practical multi-agent role modeling (manager/user/assistant/custom role) in production code.
  - Good reference for agent-tool governance patterns (telemetry, typed schemas, interruptible execution).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
