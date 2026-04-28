---
repo_name: opensolon/solon-ai
url: "https://github.com/opensolon/solon-ai"
stars: 363
forks: 55
contributors_count: 31
last_commit_date: "2026-04-23T05:37:57+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 3
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T16:25:08.912197+00:00"
model: auto
duration_s: 112.7
clone_size_kb: 24368
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`opensolon/solon-ai` is a Java framework for building LLM-powered applications with built-in agent orchestration, tool calling, RAG, and MCP connectivity. In practice, users instantiate `ReActAgent` or `TeamAgent` objects (or run declarative `solon-flow` chains) and then call them with prompts; the runtime executes multi-step reasoning, tool invocations, and routing across specialized agents. The same codebase also provides pluggable repository/search/skill modules (vector DB backends, web search, shell, REST API skills, etc.) that can be attached to agents or flow nodes. A typical output is either a final assistant answer or a traced multi-agent execution path with intermediate tool observations and routing records (`solon-ai-agent/src/main/java/org/noear/solon/ai/agent/team/TeamAgent.java:165-307`, `solon-ai-flow/src/test/resources/flow/rag_case1.chain.json:1-117`).

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen imports; it implements a **custom agent framework** on top of Solon’s own flow engine (`solon-flow`) (`solon-ai-agent/pom.xml:24-32`, repository-wide search for `langchain|langgraph|crewai|autogen` returns no matches). Core intelligence is in `ReActAgent` and `TeamAgent`, both compiling agent behavior into `Graph` structures and executing via `FlowEngine` (`solon-ai-agent/src/main/java/org/noear/solon/ai/agent/react/ReActAgent.java:95-121`, `solon-ai-agent/src/main/java/org/noear/solon/ai/agent/team/TeamAgent.java:76-91`).

`ReActAgent` is a single-agent reason-act loop with optional planning/feedback/HITL: it cycles between `ReasonTask` and `ActionTask`, parses model outputs or native tool calls, executes tools, and feeds observations back into working memory (`.../ReActAgent.java:95-115`, `.../react/task/ReasonTask.java:342-380`, `.../react/task/ActionTask.java:91-108`).

`TeamAgent` is a multi-agent container that supports multiple protocols (hierarchical, sequential, market, contract-net, blackboard, swarm, A2A). The protocol object builds/adjusts the collaboration graph and injects routing/prompt/tool policy (`.../team/TeamProtocols.java:30-78`, `.../team/TeamAgent.java:79-89`, `.../team/protocol/TeamProtocolBase.java:51-58`).

## 3. Orchestration Pattern

Closest match: **graph (state-machine) orchestration**, with protocol-specific behavior that can emulate hierarchical, sequential, swarm, blackboard, and market-like collaboration.

Control flow is explicit graph routing by route keys:

```101:107:solon-ai-agent/src/main/java/org/noear/solon/ai/agent/team/protocol/HierarchicalProtocol.java
public void buildGraph(GraphSpec spec) {
    spec.addStart(Agent.ID_START).linkAdd(TeamAgent.ID_SUPERVISOR);
    spec.addExclusive(new SupervisorTask(config)).then(ns -> {
        linkAgents(ns);
    }).linkAdd(Agent.ID_END);
```

Supervisor decisions are parsed into next-node transitions (agent name / finish marker / fallback):

```215:224:solon-ai-agent/src/main/java/org/noear/solon/ai/agent/team/task/SupervisorTask.java
String protoRoute = config.getProtocol().resolveSupervisorRoute(context, trace, decision);
if (Assert.isNotEmpty(protoRoute)) {
    routeTo(context, trace, protoRoute);
    return;
}
String finishMarker = config.getFinishMarker();
if (decision.contains(finishMarker)) {
```

ReAct is also graph-driven (`reason -> action -> reason` loop) rather than a plain while-loop (`solon-ai-agent/src/main/java/org/noear/solon/ai/agent/react/ReActAgent.java:97-114`).

## 4. Tools & External Integrations

- **LLM providers / dialects**: OpenAI, Ollama, Dashscope, Gemini, Anthropic adapters managed as modules (`solon-ai-parent/pom.xml:101-129`).
- **MCP servers (stdio/http/sse)**: `ChatModelCom` loads `mcpServers` into `McpProviders`, which expose MCP tools/prompts/resources to model calls (`solon-ai-flow/src/main/java/.../ChatModelCom.java:78-85`, `solon-ai-mcp/src/main/java/.../McpProviders.java:184-239`).
- **RAG repositories and retrieval-as-tool**: repository search, optional reranking, and `repository_query` tool for agent-side retrieval (`solon-ai-core/src/main/java/org/noear/solon/ai/rag/RepositoryTool.java:50-81`).
- **Flow-level RAG pipeline**: embedding node + repository node + chat node in declarative chain (`solon-ai-flow/src/test/resources/flow/rag_case1.chain.json:27-93`), repository component loads docs and augments prompts (`solon-ai-flow/src/main/java/.../AbsRepositoryCom.java:49-94`).
- **Web search / web fetch**: Tavily-backed repository (`solon-ai-rag-searchs/.../TavilyWebSearchRepository.java:37-47`), plus skill-level `webfetch` tool with HTML-to-Markdown conversion (`solon-ai-skills/.../WebfetchTool.java:62-152`).
- **System/terminal execution**: `ShellSkill` exposes `execute_shell` for local command execution (`solon-ai-skills/.../ShellSkill.java:127-135`).
- **REST API integration**: OpenAPI-driven tool discovery and runtime invocation (`solon-ai-skills/.../RestApiSkill.java:267-321`, `393-409`).
- **Vector DB/storage ecosystem**: many pluggable repository backends (Chroma, pgvector, Qdrant, Weaviate, Redis, Elasticsearch, etc.) via module dependencies (`solon-ai-parent/pom.xml:167-236`).

## 5. Notable Code Walkthrough

- `solon-ai-agent/src/main/java/org/noear/solon/ai/agent/team/TeamAgent.java:68-91,167-245` - Constructs protocol-defined collaboration graphs and executes them with `FlowEngine`, while managing trace/memory/session lifecycle.
- `solon-ai-agent/src/main/java/org/noear/solon/ai/agent/team/task/SupervisorTask.java:109-195,215-250` - Central manager logic: builds supervisor prompt, calls LLM, interprets decision text, commits next route, and enforces finish/routing semantics.
- `solon-ai-agent/src/main/java/org/noear/solon/ai/agent/react/task/ReasonTask.java:342-380` - Converts model output into either tool-action routing or final-answer termination; includes robust fallback behavior.
- `solon-ai-agent/src/main/java/org/noear/solon/ai/agent/react/task/ActionTask.java:304-349` - Executes actual tools (including interceptors/context merging) and returns observations into working memory.
- `solon-ai-flow/src/main/java/org/noear/solon/ai/flow/components/models/ChatModelCom.java:63-89` - Wiring point where tool providers and MCP servers are attached to chat model instances used in flow nodes.

## 6. Use-Case Mapping

The codebase clearly supports **RAG + Agents** (retrieval repositories, embedding/splitters, retrieval tool calling, multi-agent protocols), but operationally it is broader: it is a general orchestration framework where LLM agents coordinate tools/services and workflows. Given the mandatory classifier output requested below, `Workflow Automation` is defensible because the dominant abstraction is graph/protocol workflow control (supervisor routing, stage progression, protocol policies) rather than only retrieval QA (`solon-ai-agent/.../SupervisorTask.java:109-195`, `solon-ai-flow/.../ChatModelCom.java:58-136`, `solon-ai-core/.../RepositoryTool.java:50-81`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Rich multi-agent protocol library in one runtime (hierarchical, sequential, swarm, blackboard, contract-net, A2A).
- Explicit state-machine orchestration makes control flow inspectable and debuggable.
- Strong integration surface: MCP, RAG stores, web/search, shell, REST APIs, and many skills.
- ReAct implementation includes safety controls (max steps, retries, pending/HITL hooks).
- Modular Java packaging supports embedding into broader enterprise stacks.

- **Limitations:**
- Heavy reliance on prompt-engineered routing/markers can be brittle under model variance.
- Much behavior is framework-level; many concrete examples are in tests/manual flows, so production reference apps are less obvious.
- The orchestration complexity is high; configuration/protocol tuning likely has steep learning curve.
- Some protocol/tool text and safeguards are language- and convention-dependent (marker parsing, string-based route extraction).
- Interactions across many optional modules may increase integration/testing burden.

- **Research relevance:**
- Good evidence of **production-oriented MAS protocol engineering** in Java, beyond Python-centric ecosystems.
- Useful case for comparing centralized supervisor routing vs. alternative protocols under one API.
- Demonstrates hybridization of graph workflows with tool-augmented ReAct loops.
- Provides a modular benchmark surface for studying interoperability (MCP + tool skills + RAG backends).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
