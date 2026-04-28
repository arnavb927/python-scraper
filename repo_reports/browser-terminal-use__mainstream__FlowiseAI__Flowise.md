---
repo_name: FlowiseAI/Flowise
url: "https://github.com/FlowiseAI/Flowise"
stars: 52178
forks: 24196
contributors_count: 326
last_commit_date: "2026-04-22T20:58:42+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [Browser / Terminal Use]
generated_at: "2026-04-27T10:17:50.094909+00:00"
model: auto
duration_s: 97.6
clone_size_kb: 64967
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

Flowise is a low-code platform for building and running LLM workflows (“chatflows” and “agentflows”) through a visual node graph, then serving them via API/UI. In practice, users configure nodes (models, tools, memory, conditions, human approval, retrievers, etc.), and the server executes those graphs at runtime. The codebase includes both classic single-agent tool-calling agents and explicit multi-agent patterns (supervisor-worker teams and sequential agent graphs). The output users get is an orchestrated response stream plus execution artifacts (tool traces, source docs, actions, checkpoints), persisted in database-backed execution/chat records (`packages/server/src/utils/buildAgentGraph.ts:36-409`, `packages/server/src/utils/buildAgentflow.ts:1495-2362`).

## 2. Agent Framework & Architecture

The runtime is primarily **LangChain + LangGraph (JS/TS)**, with custom wrappers and extensions. Evidence includes direct imports of `StateGraph` from `@langchain/langgraph` and `AgentExecutor`/tool-calling parsers from LangChain-core/classic wrappers (`packages/server/src/utils/buildAgentGraph.ts:16`, `packages/components/src/agents.ts:256-365`). The project also includes **LlamaIndex** agent nodes, but they are marked deprecating (`packages/components/nodes/agents/LlamaIndexAgents/OpenAIToolAgent/OpenAIToolAgent_LlamaIndex.ts:31-43`).

Architecture-wise, the “intelligence” is distributed across node definitions: prompts embedded in node classes (e.g., supervisor prompt), tool-binding logic, and graph edge routing rules. Multi-agent mode initializes worker nodes first, groups them under supervisors, then compiles a LangGraph where supervisor routes to workers via `next`, terminating on `FINISH` (`packages/server/src/utils/buildAgentGraph.ts:473-613`). Sequential mode builds a richer state graph with condition nodes, LLM-to-tool conditional routing, optional human interrupts, and checkpointed continuation (`packages/server/src/utils/buildAgentGraph.ts:636-1058`).

At a higher layer, `buildAgentflow` executes generic workflow graphs (including non-LLM nodes), manages queue/dependency resolution, branching, looping, persisted execution state, and resume-from-human-input behavior (`packages/server/src/utils/buildAgentflow.ts:1925-2139`).

## 3. Orchestration Pattern

Closest fit: **graph-based orchestration (LangGraph state machine)** with two sub-patterns:
- **Hierarchical manager-worker** in Multi Agents mode (supervisor routes workers).
- **Event/state-driven graph workflow** in Sequential/Agentflow mode (conditional edges, interrupts, loopbacks).

Control flow is explicit in graph wiring:

```ts
// build multi-agent graph
workflowGraph.addEdge(worker, supervisorResult.name)
workflowGraph.addConditionalEdges(supervisorResult.name, (x: ITeamState) => x.next, {
  ...conditionalEdges,
  FINISH: END
})
workflowGraph.addEdge(START, supervisorResult.name)
```

`packages/server/src/utils/buildAgentGraph.ts:552-570`

```ts
// sequential LLM node routes to tool node based on tool_calls
if (!lastMessage.tool_calls?.length) return END
...
if (tools.some((tool) => tool.name === toolCall.name)) return toolNode.name
seqGraph.addConditionalEdges(sourceNode.name, routeMessage)
```

`packages/server/src/utils/buildAgentGraph.ts:969-993`

## 4. Tools & External Integrations

- **MCP (Model Context Protocol) servers/tools**: dynamic MCP client over stdio/SSE/HTTP, tool discovery (`tools/list`), tool invocation (`tools/call`), plus config hardening (`packages/components/nodes/tools/MCP/core.ts:1-178`, `:364-393`).
- **Hosted MCP integrations**: Browserless MCP adapter exposes web automation/scraping actions as tools (`packages/components/nodes/tools/MCP/Browserless/BrowserlessMCP.ts:20-107`).
- **Flowise as MCP server**: chatflow-specific MCP server config/token management (`packages/server/src/services/mcp-server/index.ts:57-267`).
- **HTTP/API tools**: request tools use secure fetch and parameterized schemas (`packages/components/nodes/tools/RequestsGet/core.ts:68-184`).
- **Browser-style retrieval tool**: LangChain `WebBrowser` tool wrapper (`packages/components/nodes/tools/WebBrowser/WebBrowser.ts:1-49`).
- **Code execution sandbox**: E2B code interpreter tool executes Python and returns artifacts (`packages/components/nodes/tools/CodeInterpreterE2B/CodeInterpreterE2B.ts:101-276`).
- **RAG components**: conversational retrieval tool agent accepts `BaseRetriever` and injects retrieved context into prompt (`packages/components/nodes/agents/ConversationalRetrievalToolAgent/ConversationalRetrievalToolAgent.ts:116-119`, `:341-347`).
- **Tool runtime plumbing**: custom `AgentExecutor` records `usedTools`, `sourceDocuments`, artifacts, and propagates flow context (`packages/components/src/agents.ts:361-552`).

## 5. Notable Code Walkthrough

- `packages/server/src/utils/buildAgentGraph.ts:429-613` - Core multi-agent compiler: initializes workers/supervisors, wires LangGraph edges, attaches checkpointer memory, and streams graph execution.
- `packages/components/nodes/multiagents/Supervisor/Supervisor.ts:127-373` - Supervisor prompt/tool-routing logic; forces function/tool calling across model providers and maps decision output to `next` worker or `FINISH`.
- `packages/components/nodes/multiagents/Worker/Worker.ts:161-239` - Worker construction: binds tools, builds runnable sequence + scratchpad, wraps in custom executor with max-iteration controls.
- `packages/components/nodes/sequentialagents/Agent/Agent.ts:522-613` - Sequential agent node with optional human-approval interrupts and tool-loopback edge insertion.
- `packages/server/src/utils/buildAgentflow.ts:1925-2068` - General workflow engine loop: executes queued nodes, handles dependencies/branching/looping, and persists execution state/events.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is not the best fit after code inspection. While browser-related tooling exists (WebBrowser, Browserless MCP), the repository’s core is a **visual workflow automation platform for LLM agents**: graph compilation, branching, retries, checkpoints, human-in-the-loop approvals, execution persistence, and multi-node orchestration (`packages/server/src/utils/buildAgentflow.ts:1495-2362`, `packages/server/src/utils/buildAgentGraph.ts:636-1058`).  
A better category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong graph-native orchestration with explicit state channels, conditional routing, and checkpointing (`buildAgentGraph.ts`).
  - Supports both manager-worker and sequential graph agent patterns in one runtime.
  - Rich tool telemetry propagation (`usedTools`, `sourceDocuments`, `artifacts`) for observability (`components/src/agents.ts`).
  - Practical HITL controls: interrupt-before-tool execution with approve/reject resume paths (`buildAgentGraph.ts:1002-1050`, `sequentialagents/Agent.ts:557-597`).
  - Broad integration surface (MCP, HTTP tools, retrievers, code sandbox).

- **Limitations:**
  - Orchestration complexity is high; logic is spread across large files and node classes, increasing maintenance burden.
  - Multi-agent assumes effectively one active supervisor execution stream (“should only have 1 supervisor” comment) limiting some team topologies (`buildAgentGraph.ts:601-603`).
  - Heavy dependence on prompt conventions and node-level configs can make behavior brittle across model/provider changes.
  - Security posture varies by tool; some tools are hardened (MCP validation, secureFetch), but broad pluggability increases attack surface.
  - LlamaIndex agent support exists but is explicitly deprecating, indicating framework fragmentation (`OpenAIToolAgent_LlamaIndex.ts:41-43`).

- **Research relevance:**
  - Useful real-world example of **production LangGraph orchestration** beyond toy demos.
  - Demonstrates **hybrid MAS patterns** (hierarchical and conditional graph-based) in a single platform.
  - Provides evidence for **HITL-interruptible agent execution** with resumable checkpoints.
  - Good case study for **tool-augmented LLM systems engineering** (telemetry, persistence, retries, branching).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
