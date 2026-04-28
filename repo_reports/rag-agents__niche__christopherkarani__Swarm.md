---
repo_name: christopherkarani/Swarm
url: "https://github.com/christopherkarani/Swarm"
stars: 456
forks: 29
contributors_count: 6
last_commit_date: "2026-04-18T06:24:52+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [LangChain, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:17:10.513274+00:00"
model: auto
duration_s: 85.3
clone_size_kb: 7732
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`Swarm` is a Swift framework (not an end-user app) for building and running LLM agents, multi-agent workflows, tool-calling loops, and durable executions on Apple platforms/Linux. A user typically writes Swift code that instantiates `Agent` objects, wires tools/handoffs/memory, and executes either a single agent (`agent.run(...)`) or a composed `Workflow().step(...).parallel(...).route(...)`. Under the hood, the runtime repeatedly calls an inference provider, executes requested tools, and feeds tool results back into the model until completion. The project also ships deterministic capability scenarios (`SwarmCapabilityShowcase`) that exercise handoffs, memory, MCP, workflows, and providers as runnable examples (`Sources/SwarmCapabilityShowcaseSupport/CapabilityShowcase.swift:202-309`, `:450-564`).

## 2. Agent Framework & Architecture

This repo is **custom**, not LangChain/AutoGen/CrewAI/LangGraph. The core abstractions are native Swift types/protocols (`Agent`, `AgentRuntime`, `Workflow`, `Tool`, `InferenceProvider`) in `Sources/Swarm`, with provider adapters over Conduit/Hive rather than Python agent libraries (`Sources/Swarm/Agents/Agent.swift:45-61`, `Sources/Swarm/Core/AgentRuntime.swift`, `Sources/Swarm/Providers/Conduit/ConduitInferenceProvider.swift:9-17`).

Architecture has two main orchestration layers:

1. **Agent-level loop**: `Agent` maintains a model→tools→model iterative loop, injects memory context, handles guardrails, and can hand off to other agents as tool calls (`Agent.swift:1103-1389`, `:1794-1928`).
2. **Workflow-level composition**: `Workflow` composes multiple `AgentRuntime`s with sequential, parallel, routing, fallback, repeat-until, and timeout semantics (`Workflow.swift:89-95`, `:215-313`, `:501-559`).

There is also an internal graph runtime built on Hive for deterministic/durable execution (`Sources/Swarm/Internal/GraphRuntime/ChatGraph.swift:116-173`, `Sources/Swarm/Workflow/WorkflowDurableEngine.swift:117-179`), so the “intelligence” is split across prompt instructions, tool schemas, handoff configuration, and graph/workflow control logic rather than one centralized planner class.

## 3. Orchestration Pattern

Closest match: **hybrid graph + hierarchical + sequential/parallel workflow orchestration** (not peer-to-peer swarm).  
- Agent internals are a graph-like tool loop (model/tool/model).  
- Cross-agent delegation is hierarchical via explicit handoff tools.  
- Multi-agent pipelines are composed as workflow DAG-like steps (sequential/parallel/route/repeat).

Control-flow evidence:

```1872:1890:Sources/Swarm/Agents/Agent.swift
let result = try await executeWithinRemainingTimeout(startTime: startTime) {
    try await targetAgent.run(handoffInput, session: nil, observer: observer)
}
conversationHistory.append(.toolResult(
    toolName: parsedCall.name,
    result: result.output,
    toolCallID: parsedCall.id
))
```

```506:523:Sources/Swarm/Workflow/Workflow.swift
case .parallel(let agents, let merge):
    let results = try await withThrowingTaskGroup(of: AgentResult.self, returning: [AgentResult].self) { group in
        for agent in agents {
            group.addTask {
                try await agent.run(inputSnapshot, session: nil, observer: nil)
            }
        }
        ...
    }
```

And the internal graph router loops until no pending tool calls:

```154:170:Sources/Swarm/Internal/GraphRuntime/ChatGraph.swift
let router: HiveRouter<Schema> = { store in
    let pending = try store.get(Schema.pendingToolCallsKey)
    return pending.isEmpty ? .end : .to([nodeIDs.tools])
}
...
builder.addRouter(from: nodeIDs.model, router)
```

## 4. Tools & External Integrations

- **LLM providers via Conduit** (OpenAI/OpenRouter/Anthropic/Ollama/MLX/Foundation routing through provider adapters): `Sources/Swarm/Providers/Conduit/ConduitInferenceProvider.swift:9-17`, `:91-182`.
- **MCP servers/tools/resources**:
  - Multi-server MCP client aggregation: `Sources/Swarm/MCP/MCPClient.swift:56-71`, `:174-249`, `:340-383`.
  - HTTP MCP transport (JSON-RPC over HTTP with retry): `Sources/Swarm/MCP/HTTPMCPServer.swift:50-57`, `:106-182`, `:293-356`.
  - MCP-to-Swarm tool bridge: `Sources/Swarm/MCP/MCPToolBridge.swift:36-74`, `:120-171`.
- **Web search/fetch/grounding tool** (`websearch` with search/fetch/ground/recall/expand/refresh modes): `Sources/Swarm/Tools/WebSearchTool.swift:8-16`, `:107-121`, `:275-282`.
- **RAG memory integration**:
  - Agent pulls memory context before LLM call: `Sources/Swarm/Agents/Agent.swift:1121-1138`.
  - Semantic vector memory over embedding providers: `Sources/Swarm/Memory/VectorMemory.swift:14-19`, `:137-177`, `:211-234`.
- **Agent-as-tool composition** (hierarchical delegation without separate workflow object): `Sources/Swarm/Tools/AgentTool.swift:35-52`, `:90-108`.
- **Zoni RAG tool stub exists but is not production-wired** (currently throws pipeline-not-configured): `Sources/Swarm/Tools/ZoniSearchTool.swift:15-24`, `:47-65`.

## 5. Notable Code Walkthrough

- `Sources/Swarm/Agents/Agent.swift:1103-1389` — core iterative runtime: retrieves memory context, builds prompt/messages, calls provider with tool schemas, executes tool calls, and exits on final content or max iterations.
- `Sources/Swarm/Agents/Agent.swift:1794-1928` — handoff mechanism: represents target agents as synthetic tool schemas and transfers execution to selected target agent when that handoff tool is invoked.
- `Sources/Swarm/Workflow/Workflow.swift:89-95,215-313,501-559` — fluent orchestrator implementing `.step`, `.parallel`, `.route`, `.repeatUntil`, `.fallback`, with explicit per-step execution semantics.
- `Sources/Swarm/Internal/GraphRuntime/ChatGraph.swift:116-173,745-895` — compiled Hive graph implementing deterministic model/tools loop and routing based on pending tool calls.
- `Sources/Swarm/MCP/MCPClient.swift:174-249,340-383` — concrete external-tool plumbing for aggregating MCP tools/resources across multiple servers with caching and deduplication.

## 6. Use-Case Mapping

The assigned category **RAG + Agents** is partially true: the runtime explicitly supports retrieval-augmented context (`Agent` reads memory context before prompting; `VectorMemory` performs embedding similarity search) and combines that with tool-calling agents (`Agent.swift:1121-1138`, `VectorMemory.swift:148-177`).

However, this repository is broader and more fundamentally a **general agent orchestration framework** rather than a single RAG system. It provides workflow composition, handoffs, resilience, durable execution, MCP integration, and provider abstraction as first-class framework capabilities. So for repository-level classification, **Workflow Automation** is a better primary fit.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong multi-agent primitives (handoffs + workflow composition + agent-as-tool) in one coherent runtime (`Agent.swift`, `Workflow.swift`, `AgentTool.swift`).
  - Durable/checkpointed execution through Hive-backed graph engine (`WorkflowDurableEngine.swift:117-179`).
  - Real interoperability surface via MCP client/HTTP transport/bridge (`MCPClient.swift`, `HTTPMCPServer.swift`, `MCPToolBridge.swift`).
  - Explicit memory/RAG integration in the main inference loop rather than bolt-on utilities (`Agent.swift:1121-1138`).
  - Deterministic capability scenarios covering major subsystems for regression evidence (`CapabilityShowcase.swift:202-309`, `:450-906`).

- **Limitations:**
  - Heavy framework complexity; many abstractions raise adoption/learning cost for small use cases.
  - Some integrations are scaffolded but not fully operational (e.g., `ZoniSearchTool` currently throws not configured).
  - Handoff flow in current `Agent` returns on first handoff result, so deeper collaborative/iterative team dialog patterns are less explicit by default (`Agent.swift:1909-1911`).
  - Predominantly library-level tests/examples; fewer domain-specific end-to-end real-world apps in-repo.
  - Uses `@unchecked Sendable` in workflow step enum (`Workflow.swift:90-95`), which may concern strict-concurrency purists.

- **Research relevance:**
  - Evidence of production-oriented MAS engineering in Swift: typed tools, explicit handoff semantics, and orchestrated workflows.
  - Useful case study for integrating graph runtimes with agent loops (Hive graph + tool-calling loop).
  - Demonstrates practical MCP tool/resource federation as part of agent runtime architecture.
  - Illustrates how RAG memory retrieval can be integrated into iterative tool-calling agents in a non-Python ecosystem.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
