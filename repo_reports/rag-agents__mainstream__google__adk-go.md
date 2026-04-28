---
repo_name: google/adk-go
url: "https://github.com/google/adk-go"
stars: 7639
forks: 650
contributors_count: 47
last_commit_date: "2026-04-22T08:30:40+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T11:58:38.785245+00:00"
model: auto
duration_s: 92.7
clone_size_kb: 9512
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`google/adk-go` is a Go SDK for building and running agent systems, not a single prebuilt app. A developer defines agents (LLM agents, workflow agents, or remote A2A agents), wires tools/services (memory, artifacts, MCP, etc.), and runs them through the `runner`. In practice, users run example binaries or their own Go program (often via the launcher) that takes user input, executes agent/tool loops, and streams back events/responses. The output is a session-backed event trace plus model/tool responses, with optional HTTP serving modes (`adkrest`, `agentengine`, `a2a`) for deployment.

## 2. Agent Framework & Architecture

This repo uses a **custom framework (Google ADK for Go)**, not LangGraph/LangChain/CrewAI/AutoGen. Evidence: core abstractions are native packages like `agent`, `agent/llmagent`, `runner`, and `internal/llminternal` (`agent/agent.go`, `agent/llmagent/llmagent.go`, `runner/runner.go`). Model integration is through `google.golang.org/genai` and ADK model wrappers, not external agent frameworks.

Architecture is centered on an **agent tree** plus an event-driven run loop. `runner.Run` resolves session state, picks the active agent (including transfer continuation), creates invocation context, and streams events while appending non-partial events to session storage (`runner/runner.go:128-267`, `runner/runner.go:327-403`). Agent definitions include `SubAgents`, callback hooks, and configurable run behavior (`agent/agent.go:76-107`).

“Intelligence” primarily lives in `llminternal.Flow`: request processors build LLM requests (instructions, tools, transfer tooling, schema behavior), model calls are made, tool calls are executed, and transfer actions can recursively invoke target agents (`internal/llminternal/base_flow.go:73-91`, `:98-124`, `:126-246`). Transfer logic is itself prompt/tool mediated via `transfer_to_agent` injection (`internal/llminternal/agent_transfer.go:68-96`, `:99-154`, `:297-317`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) + workflow composition** (sequential/parallel/loop), implemented as an agent tree with transfer-based routing.

Control flow through explicit sub-agent workflow runners:

```65:75:agent/workflowagents/sequentialagent/agent.go
func (a *sequentialAgent) Run(ctx agent.InvocationContext) iter.Seq2[*session.Event, error] {
	return func(yield func(*session.Event, error) bool) {
		for _, subAgent := range ctx.Agent().SubAgents() {
			for event, err := range subAgent.Run(ctx) {
				if !yield(event, err) { return }
			}
		}
	}
}
```

LLM-mediated handoff between agents via `transfer_to_agent`:

```228:242:internal/llminternal/base_flow.go
if ev.Actions.TransferToAgent == "" { return }
nextAgent := f.agentToRun(ctx, ev.Actions.TransferToAgent)
if nextAgent == nil { yield(nil, fmt.Errorf("failed to find agent: %s", ev.Actions.TransferToAgent)); return }
for ev, err := range nextAgent.Run(ctx) {
	if !yield(ev, err) || err != nil { return }
}
```

This is not a LangGraph-style explicit state graph; it is runtime routing in a parent/sub-agent tree plus dedicated workflow-agent primitives (`sequentialagent`, `parallelagent`, `loopagent`).

## 4. Tools & External Integrations

- **LLM backend (Gemini / GenAI API):** model calls via `GenerateContent` inside ADK flow (`internal/llminternal/base_flow.go:401-449`), examples instantiate Gemini models (`examples/quickstart/main.go:37-52`).
- **Function tools (custom Go functions):** tool declarations and `Run` are executed from model function-calls, including parallel handling (`internal/llminternal/base_flow.go:581-685`).
- **MCP servers:** `mcptoolset` connects to MCP transport/client, lists tools, converts to ADK tools (`tool/mcptoolset/set.go:27-56`, `:107-129`); example wires local/GitHub MCP (`examples/mcp/main.go:64-86`, `:107-123`).
- **Google Search built-in tool:** model-native search tool via `genai.GoogleSearch` (`tool/geminitool/google_search.go:24-45`), used in quickstart (`examples/quickstart/main.go:49-51`).
- **Memory/RAG-like retrieval:** `load_memory` tool calls `SearchMemory` for user-scoped memory entries (`tool/loadmemorytool/tool.go:82-108`), memory interface supports session ingestion + query (`memory/service.go:27-39`), end-to-end example in `examples/tools/loadmemory/main.go:50-102`.
- **Artifacts (file/context retrieval):** `load_artifacts` tool lists/loads artifact payloads and appends them into request context (`tool/loadartifactstool/load_artifacts_tool.go:118-152`, `:154-220`).
- **Remote agent protocol (A2A):** remote agents created with A2A client/card resolution and stream processing (`agent/remoteagent/a2a_agent.go:121-158`, `:164-263`), with local server/client demo (`examples/a2a/main.go:65-101`, `:115-130`).
- **Session persistence backends:** in-memory/database/Vertex-backed session services under `session/*`; runner persists event history (`runner/runner.go:141-164`, `:255-261`).

## 5. Notable Code Walkthrough

- `internal/llminternal/base_flow.go:98-246` - Core LLM execution loop: preprocess request, call model, emit events, execute tools, and trigger agent transfer. This is the operational heart of ADK agent behavior.
- `internal/llminternal/agent_transfer.go:68-97,297-317` - Injects transfer tool + prompt instructions describing eligible target agents, enabling model-driven delegation across the agent tree.
- `runner/runner.go:128-267,327-360` - Orchestrates full run lifecycle: session lookup/create, active-agent selection, context wiring (memory/artifacts/plugins), event streaming, and persistence.
- `agent/workflowagents/parallelagent/agent.go:67-128` - Implements true parallel sub-agent execution with isolated branch contexts and coordinated event acknowledgement.
- `tool/agenttool/agent_tool.go:118-251` - Wraps an agent as a callable tool, letting one agent invoke another through the tool interface (important for compositional multi-agent patterns).

## 6. Use-Case Mapping

Assigned label `RAG + Agents` is **partially accurate but not primary**. The repo does include retrieval-style behavior via memory/artifact loading tools (`tool/loadmemorytool/tool.go`, `tool/loadartifactstool/load_artifacts_tool.go`), and examples demonstrate memory-assisted answering (`examples/tools/loadmemory/main.go`). However, the main codebase is broader: it is a general agent runtime emphasizing orchestration patterns (sequential/parallel/loop), delegation, tool-calling, remote agent interop, and server deployment. A better single primary category is **Workflow Automation**, with RAG as one supported capability rather than the core identity.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, composable runtime abstractions for agent trees, sessions, and tools (`agent`, `runner`, `llminternal`).
  - Multiple orchestration modes built-in (sequential, parallel, loop, transfer-driven delegation).
  - Strong integration surface (MCP, A2A, artifacts, memory, plugins, REST/agent-engine servers).
  - Event-centric architecture with callback/plugin hooks supports observability and control.
  - Practical Go-first implementation with many runnable examples and tests.

- **Limitations:**
  - No explicit global workflow graph DSL; routing is implicit via transfer/tool behavior.
  - Transfer behavior is prompt/tool mediated and can depend on LLM reliability.
  - Memory interface is generic; no built-in sophisticated vector DB pipeline in core (beyond pluggable memory service + examples).
  - Some TODOs in critical flow code (termination/partial handling/runner-transfer notes) indicate evolving semantics.
  - Multi-agent quality controls (e.g., formal planner/verifier layers) are left to user composition.

- **Research relevance:**
  - Evidence of production-oriented **hierarchical multi-agent orchestration** in Go.
  - Useful case for studying **tool-augmented delegation** (`transfer_to_agent` as a callable policy mechanism).
  - Demonstrates **hybrid local/remote MAS interop** (A2A protocol + MCP tool ecosystem).
  - Good reference for **event-sourced agent runtime** design (session event streams, callbacks, plugin interception).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
