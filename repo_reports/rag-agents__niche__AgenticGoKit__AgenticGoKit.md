---
repo_name: AgenticGoKit/AgenticGoKit
url: "https://github.com/AgenticGoKit/AgenticGoKit"
stars: 143
forks: 30
contributors_count: 7
last_commit_date: "2026-04-22T02:17:51+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:55:59.248366+00:00"
model: auto
duration_s: 93.1
clone_size_kb: 43361
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`AgenticGoKit` is a Go framework for building LLM-powered agents and composing them into executable workflows (sequential, parallel, DAG, loop, route-based). A user typically builds agents with `v1beta.NewBuilder(...)`, wires them into a workflow (`NewSequentialWorkflow`, etc.), and runs the workflow on an input string to get per-step outputs, final output, timing, and token usage (`v1beta/workflow.go:27-57`, `v1beta/workflow.go:259-326`). Under the hood, agents can call many LLM providers, retrieve RAG context from memory/vector backends, and execute tools including MCP tools (`v1beta/agent_impl.go:355-409`, `v1beta/agent_impl.go:418-467`). So the practical output is not just a chat response: it is an orchestrated multi-step pipeline with memory, tool execution, and observability data.

## 2. Agent Framework & Architecture

This is a **custom framework**, not LangChain/LangGraph/CrewAI/AutoGen. The code defines its own agent, orchestrator, runner, workflow, and tool abstractions (`internal/core/agent.go:7-31`, `internal/core/orchestrator.go:5-19`, `v1beta/workflow.go:27-57`). LLM integration is also custom via internal adapters/factories rather than external orchestration frameworks (`internal/llm/factory.go:124-163`).

Architecture-wise, the “intelligence” sits primarily in agent runtime code and prompts: system prompts in config, optional memory enrichment (RAG), and tool-calling loops in `realAgent.execute(...)` (`v1beta/agent_impl.go:306-376`, `v1beta/agent_impl.go:418-467`, `v1beta/agent_impl.go:1552-1648`). The v1beta workflow layer orchestrates multiple agents as steps with conditions/dependencies (`v1beta/workflow.go:59-67`, `v1beta/workflow.go:1084-1199`, `v1beta/workflow.go:1351-1509`). There is also a lower-level event/route orchestration engine in `internal/core` + `internal/orchestrator` for event dispatch and chained emissions (`internal/core/runner.go:303-384`, `internal/core/runner.go:413-499`).

## 3. Orchestration Pattern

Closest match: **event-driven + workflow automation hybrid**.  
- Event-driven core: `Runner` consumes events, dispatches through orchestrator, and emits follow-up events based on output route metadata (`internal/core/runner.go:303-349`, `internal/core/runner.go:455-487`).  
- Workflow layer: explicit sequential/parallel/DAG/loop step orchestration over multiple agents (`v1beta/workflow.go:279-290`, `v1beta/workflow.go:1201-1349`, `v1beta/workflow.go:1511-1689`).

Control-flow excerpt 1 (event routing):

```343:349:internal/core/runner.go
if agentErr == nil {
    Logger().Debug().Str("event_id", event.GetID()).Msg("Runner loop: Dispatching event to orchestrator")
    agentResult, agentErr = orchestrator.Dispatch(eventCtx, event)
}
```

Control-flow excerpt 2 (sequential step chaining):

```64:83:internal/orchestrator/sequential.go
for i, agentName := range o.agentSequence {
    handler, exists := o.handlers[agentName]
    ...
    result, err := handler.Run(ctx, event, state)
    ...
    state = result.OutputState
}
```

## 4. Tools & External Integrations

- **LLM providers**: OpenAI, Azure OpenAI, Ollama, OpenRouter, HuggingFace, vLLM, MLflow Gateway, BentoML, Anthropic, Foundry Local (`internal/llm/factory.go:15-27`, `internal/llm/factory.go:137-163`).
- **Memory / vector / RAG**: in-memory, pgvector, Weaviate providers with embedding service wiring and RAG defaults (`internal/memory/factory.go:13-41`, `internal/memory/factory.go:89-110`); pgvector plugin registration (`plugins/memory/pgvector/pgvector.go:8-30`).
- **MCP tool ecosystem**: tool discovery and execution wrappers (`v1beta/tool_discovery.go:50-73`, `v1beta/tool_discovery.go:181-277`), plus unified MCP manager supporting TCP, HTTP SSE, HTTP streaming, WebSocket, and stdio transports (`plugins/mcp/unified/unified.go:72-79`, `plugins/mcp/unified/unified.go:938-1018`).
- **Agent tool-calling loop**: parses tool calls, executes tools, and optionally re-prompts LLM with tool outputs (`v1beta/agent_impl.go:418-467`, `v1beta/agent_impl.go:1552-1648`, `v1beta/agent_impl.go:1662-1782`).
- **External web search API**: Brave Search integration via `BRAVE_API_KEY` (`internal/tools/web_search.go:29-46`, `internal/tools/web_search.go:68-104`).
- **Observability**: OpenTelemetry spans are pervasive in workflows/agents/tool calls (`v1beta/workflow.go:537-553`, `v1beta/agent_impl.go:285-295`, `v1beta/tool_discovery.go:182-217`).

## 5. Notable Code Walkthrough

- `v1beta/agent_impl.go:277-565` - Core runtime of the main agent implementation: prompt assembly, RAG enrichment, LLM call, tool-call handling, memory persistence, and result packaging.
- `v1beta/workflow.go:259-326` - Central workflow `Run` entrypoint that dispatches by mode (sequential/parallel/DAG/loop) and aggregates execution metadata.
- `v1beta/workflow.go:1084-1199` - Concrete sequential orchestration logic that executes each step agent and propagates output to next step.
- `internal/core/runner.go:253-411` - Event loop for lower-level orchestration; runs callbacks, dispatches events via orchestrator, and handles agent errors.
- `plugins/mcp/unified/unified.go:779-860` - Actual MCP tool execution path selecting server/client transport and invoking `CallTool`.

## 6. Use-Case Mapping

The repo **does implement RAG + Agents** technically (memory providers, `BuildContext`, prompt enrichment, vector-backed retrieval in agent execution: `core/unified_agent.go:119-157`, `v1beta/agent_impl.go:355-376`, `internal/memory/factory.go:26-57`). It also clearly supports multi-agent orchestration at runtime (workflow steps and orchestrators).

However, the dominant framing and reusable core in this codebase is broader **workflow orchestration for LLM agents** (sequential/parallel/DAG/loop/event routing) rather than a pure RAG-first architecture. So the better final category is **Workflow Automation**, with RAG as a major capability.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Multi-pattern orchestration in one framework (sequential, parallel, DAG, loop, route/event-driven).
  - Strong provider/tool extensibility via plugin factories (LLM, memory, MCP transports).
  - Practical agent runtime combining LLM + tools + memory/RAG in one execution path.
  - Built-in observability instrumentation across agents/workflows/tools.
  - Concrete examples showing multi-agent pipelines (e.g., researcher→reporter workflow).

- **Limitations:**
  - Some MCP-aware internals include placeholder behavior (e.g., direct tool execution fallback text in `internal/mcp/mcp_agent.go:291-310`), indicating uneven maturity across layers.
  - Multiple overlapping APIs (`internal/core` vs `v1beta`) increase conceptual complexity.
  - Tool-call parsing uses mixed native/text mechanisms, which may be brittle across model behaviors.
  - Documentation/examples are broad, but production hardening details (policy/safety/robust retries across all integrations) are inconsistent by component.
  - “DAG” execution in streaming path currently delegates to sequential in one branch (`v1beta/workflow.go:796-800`).

- **Research relevance:**
  - Good evidence of **modular orchestration design** for agent systems in a compiled language (Go), not Python-first ecosystems.
  - Useful case for studying **hybrid orchestration** (event-driven dispatch + explicit workflow DAG/loop semantics).
  - Demonstrates **tool-augmented and memory-augmented agent execution** with MCP interoperability.
  - Suitable as an engineering reference for **observability-instrumented MAS runtimes**.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
