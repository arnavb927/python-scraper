---
repo_name: smallnest/langgraphgo
url: "https://github.com/smallnest/langgraphgo"
stars: 235
forks: 36
contributors_count: 10
last_commit_date: "2026-02-24T14:00:34+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 3
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T16:39:39.702413+00:00"
model: auto
duration_s: 84.4
clone_size_kb: 34143
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`smallnest/langgraphgo` is a Go framework for building LLM applications as typed state graphs, with prebuilt agent patterns and RAG components. In practice, users run Go programs (mostly from `examples/*/main.go`) that construct graphs, plug in an LLM (`langchaingo` models), add tools/retrievers, compile, and invoke with an input state (e.g., `examples/supervisor/main.go:52-194`, `examples/rag_pipeline/main.go:16-100`). The output is an evolved state containing conversation messages, tool results, and/or generated answers. The repo is not just demos: core runtime in `graph/` executes nodes, merges state, and routes conditionally (`graph/state_graph.go:171-391`). It is a general-purpose agent workflow engine, with RAG as one major supported workload.

## 2. Agent Framework & Architecture

The primary framework is **custom LangGraph-style orchestration implemented in Go** (`graph.StateGraph`, `StateRunnable`), not Python LangGraph. It integrates with **LangChainGo** abstractions for models and tools (`github.com/tmc/langchaingo/llms`, `tools`) throughout prebuilt agents (`prebuilt/react_agent.go:8-11`, `prebuilt/supervisor.go:9-11`, `prebuilt/create_agent.go:12-14`). I did not find runtime use of CrewAI/AutoGen/LlamaIndex internals in core agent execution.

Architecture is graph-centric: users define nodes as functions `func(ctx, state) -> state`, connect static/conditional edges, then `Compile()` and `Invoke()` (`graph/state_graph.go:83-117`, `141-151`, `171-185`). Intelligence typically lives in node-level LLM calls plus prompt templates/tool schemas. For example, the generic agent node serializes available tools into OpenAI-style function schemas and calls `GenerateContent(...WithTools...)` (`prebuilt/create_agent.go:135-179`), while a supervisor node prompts a routing decision and parses tool-call JSON (`prebuilt/supervisor.go:50-76`).

The repo includes multiple agent templates: ReAct, Supervisor, Planning, Reflection, PTC/code-executing agent, etc. (`prebuilt/*.go`, `ptc/ptc_agent.go`). Multi-agent behavior is explicit in supervisor/planning patterns where several runnable agents/nodes are coordinated by a controller graph (`prebuilt/supervisor.go:78-99`, `prebuilt/planning_agent.go:33-130`).

## 3. Orchestration Pattern

Closest match: **graph (LangGraph-style state machine)**, with optional **hierarchical manager-worker** behavior in supervisor/planning agents.

Control flow is graph-edge driven with conditional routing:
`prebuilt/react_agent.go:156-168`
```go
workflow.SetEntryPoint("agent")
workflow.AddConditionalEdge("agent", func(ctx context.Context, state map[string]any) string {
    messages := state["messages"].([]llms.MessageContent)
    lastMsg := messages[len(messages)-1]
    for _, part := range lastMsg.Parts {
        if _, ok := part.(llms.ToolCall); ok { return "tools" }
    }
    return graph.END
})
workflow.AddEdge("tools", "agent")
```

The runtime executes current nodes (including fan-out) and determines next nodes from conditional/static edges:
`graph/state_graph.go:261-269`
```go
results, errorsList := r.executeNodesParallel(ctx, currentNodes, state, config, runID)
processedResults, nextNodesFromCommands := r.processNodeResults(results)
state, mergeErr = r.mergeState(ctx, state, processedResults)
```

Manager-worker hierarchy appears in supervisor orchestration where a supervisor picks next worker (`MathExpert`, etc.) and loops:
`prebuilt/supervisor.go:87-97`.

## 4. Tools & External Integrations

- **LLM providers via LangChainGo/OpenAI-style APIs**: agent nodes call `llms.Model.GenerateContent` and use tool/function calling (`prebuilt/create_agent.go:178-199`, `prebuilt/supervisor.go:57-59`).
- **Web search APIs**: Tavily and Exa tools via HTTP (`tool/tavily.go:37-58`, `73-121`; `tool/exa.go:36-57`, `71-127`).  
- **General web fetch/scrape**: HTML fetch + text extraction with goquery (`tool/web_tool.go:11-56`).
- **Shell / code execution tools**: executes bash scripts and TypeScript (`tool/shell_tool.go:42-75`); PTC agent generates code then executes via tool node (`ptc/ptc_agent.go:60-87`, `109-120`).
- **MCP servers**: MCP tools are wrapped into `langchaingo` tools and invoked through MCP client (`adapter/mcp/mcp.go:13-19`, `60-86`).
- **RAG vector stores**: in-memory vector store (`rag/store/vector.go:12-67`), Chroma v2 HTTP backend (`rag/store/chromav2.go:15-30`, `210-291`, `293-384`), plus graph store support with FalkorDB (`rag/store/falkordb.go:15-23`, `88-172`).
- **RAG retriever-as-tool adapter**: wraps RAG engine as callable tool for agents (`rag/langgraph_adapter.go:50-92`).

## 5. Notable Code Walkthrough

- `graph/state_graph.go:171-391` - Core execution engine: initializes state with schema, runs active nodes (parallel-capable), merges updates, handles interrupts/checkpoints/callbacks, and resolves next nodes.
- `prebuilt/create_agent.go:52-277` - Canonical single-agent graph template (`agent -> tools -> agent`) with function-calling tool schemas, iteration limits, optional system prompt/state modifiers, and optional skill discovery.
- `prebuilt/supervisor.go:25-99` - Multi-agent coordinator: supervisor LLM chooses next worker via constrained `route` function tool and conditional edge routing back to workers/END.
- `prebuilt/planning_agent.go:33-130` - Planner-executor pattern: LLM emits JSON workflow plan; code parses it and constructs a dynamic graph at runtime before execution.
- `rag/pipeline.go:107-173` and `245-347` - End-to-end RAG graph pipelines (basic/advanced/conditional), including retrieval, rerank, generation, and citation formatting nodes.

## 6. Use-Case Mapping

This repo clearly supports `RAG + Agents`, but its **primary implemented pattern is broader workflow automation for LLM tasks**. RAG is realized through graph-based retrieval/generation pipelines (`rag/pipeline.go:107-231`) and through wrapping retrieval as a tool callable by agents (`rag/langgraph_adapter.go:50-92`). Agentic behavior is realized by iterative tool-using agents (`prebuilt/create_agent.go:109-275`) and multi-agent supervision/planning (`prebuilt/supervisor.go:25-99`, `prebuilt/planning_agent.go:155-253`).  

Given scope and code distribution, the assigned label is partially correct; a better single category is **Workflow Automation** (with strong RAG modules).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong typed graph runtime in Go with conditional routing, parallel node execution, interrupts, and callbacks (`graph/state_graph.go:238-375`, `489-691`).
  - Multiple concrete agent orchestration templates (ReAct, supervisor, planner, reflection, PTC) in reusable constructors (`prebuilt/*.go`, `ptc/ptc_agent.go`).
  - Practical integration surface: tool calling, MCP, web search providers, vector/graph stores (`prebuilt/create_agent.go`, `adapter/mcp/mcp.go`, `rag/store/*`).
  - RAG modeled as first-class graph pipelines rather than ad-hoc chaining (`rag/pipeline.go`).

- **Limitations:**
  - Some advanced components are scaffold-like; e.g., fallback search node in RAG is a placeholder metadata flag, not real retrieval (`rag/pipeline.go:302-310`).
  - Tool I/O contract is mostly string-based, which can force brittle argument parsing for complex tools (`prebuilt/tool_executor.go:37-45`, `prebuilt/create_agent.go:223-244`).
  - Planning agent trusts LLM-produced JSON plans and dynamic edge creation with minimal validation beyond node existence (`prebuilt/planning_agent.go:174-177`, `200-229`).
  - Framework breadth is high, but many behaviors depend on user-provided prompts/model quality rather than strict symbolic guarantees.

- **Research relevance:**
  - Evidence for production-oriented **graph-based agent orchestration in a systems language (Go)**, not Python-only ecosystems.
  - Useful case for studying **manager-worker routing via LLM function-calling constraints** (`prebuilt/supervisor.go`).
  - Demonstrates convergence of **RAG pipelines and tool-using agents** under one state-machine runtime (`rag/pipeline.go`, `rag/langgraph_adapter.go`, `prebuilt/create_agent.go`).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
