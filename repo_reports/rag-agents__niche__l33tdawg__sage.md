---
repo_name: l33tdawg/sage
url: "https://github.com/l33tdawg/sage"
stars: 211
forks: 19
contributors_count: 4
last_commit_date: "2026-04-23T02:53:09+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:46:16.668494+00:00"
model: auto
duration_s: 82.0
clone_size_kb: 26147
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`l33tdawg/sage` is a Go-based infrastructure project that gives AI agents persistent, governed memory rather than a stateless chat context. In practice, a user runs `sage-gui serve` (or Docker), connects an LLM client over MCP, and the client can call SAGE tools (`sage_turn`, `sage_recall`, `sage_pipe`, etc.) to store/retrieve memories and coordinate with other agents. Memory writes are routed through signed API calls and consensus-style validation logic before becoming committed, queryable records. The output is not an end-user chatbot app; it is a memory + coordination backend (with dashboard and SDKs) that external LLM agents use at runtime.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph, LangChain, CrewAI, AutoGen, or LlamaIndex in the core runtime (no such imports in `go.mod` or server code). The agent layer is a **custom MCP + REST architecture** implemented in Go (`internal/mcp/server.go`, `internal/mcp/tools.go`) with optional Python SDK clients (`sdk/python/src/sage_sdk/client.py`).

Architecturally, SAGE sits between LLM runtimes and storage/consensus services. The MCP server exposes tool calls over JSON-RPC (`tools/list`, `tools/call`) and translates those into signed REST operations (`internal/mcp/server.go:130-147`, `429-484`). “Intelligence” mostly lives in tool-level policy prompts/instructions and lifecycle methods (`sage_inception`, `sage_turn`, `sage_reflect`) rather than in a planner model inside this repo (`internal/mcp/tools.go:759-997`, `647-757`, `999-1061`).

Multi-agent behavior is enabled through an agent pipeline: one agent can enqueue work for another, recipients claim/process inbox items, and results are returned/journaled (`api/rest/pipe_handler.go:19-134`, `136-177`, `201-270`; `internal/mcp/tools.go:1519-1712`). So SAGE provides coordination substrate for multiple external LLM agents, not an in-process multi-agent reasoning graph.

## 3. Orchestration Pattern

Closest match: **event-driven + mailbox workflow orchestration** (custom “other” pattern), with light sequential phases inside individual tools.

Control flow is asynchronous across agents through pipeline inbox/result events:

```go
// api/rest/pipe_handler.go:161-170
items, err := pipeStore.GetInbox(r.Context(), agentID, provider, limit)
// Auto-claim all returned items
for _, item := range items {
    _ = pipeStore.ClaimPipeline(r.Context(), item.PipeID, agentID)
    item.Status = "claimed"
}
```

And each `sage_turn` executes a fixed local sequence (recall -> store observation -> check pipeline):

```go
// internal/mcp/tools.go:669-676,736-752
// Phase 1: Recall ...
// ...
// Phase 2: Store ...
if observation != "" && !isLowValueObservation(observation) && !s.similarMemoryExists(ctx, observation, domain) {
    if err := s.storeMemory(ctx, observation, domain, "observation", 0.80); err != nil { ... }
}
// Phase 3: Pipeline — check for incoming work and completed results.
pipeData := s.checkPipelineInbox(ctx)
```

So there is no central planner-worker tree or LangGraph state machine; orchestration emerges from tool-triggered events and shared queues.

## 4. Tools & External Integrations

- **MCP server integration** (`internal/mcp/server.go`, `cmd/sage-gui/mcp.go`): stdio JSON-RPC server exposing SAGE tools to external LLMs.
- **REST API backend** (`api/rest/server.go`): signed Ed25519-authenticated endpoints for memory, agents, governance, and pipeline.
- **CometBFT consensus** (`go.mod`, `api/rest/agent_handler.go`): transactions are signed/encoded/broadcast to chain-backed state.
- **Embedding service via local Ollama** (`internal/embedding/ollama.go`, `api/rest/embed_handler.go`): `/v1/embed` calls local Ollama (`/api/embed`) using `nomic-embed-text`; fallback/search mode indicated by `/v1/embed/info`.
- **Vector/database stores**:
  - PostgreSQL + pgvector (`go.mod` includes `pgx` and `pgvector-go`)
  - SQLite and Badger stores (`internal/store/*`, route/store wiring in `api/rest/server.go`).
- **Agent-to-agent pipeline service** (`api/rest/pipe_handler.go`, MCP wrappers in `internal/mcp/tools.go`): send/inbox/claim/result workflow.
- **Python SDK integration** (`sdk/python/src/sage_sdk/client.py`): programmatic access to all memory, pipeline, and governance endpoints.

No browser automation framework (Playwright is only for repo E2E tests), and no shell-execution tools for agents in core orchestration.

## 5. Notable Code Walkthrough

- `internal/mcp/server.go:45-97,130-180,200-296` - Core MCP runtime: JSON-RPC handling, tool dispatch, boot instructions, turn-discipline enforcement, and signed REST bridging.
- `internal/mcp/tools.go:21-299,647-757,1519-1712` - Defines tool surface (`sage_remember`, `sage_recall`, `sage_turn`, `sage_pipe`, etc.) and implements memory lifecycle plus pipeline inbox/results logic.
- `api/rest/pipe_handler.go:19-134,136-177,201-270` - Server-side multi-agent mailbox: send tasks to agent/provider, auto-claim inbox, return result, and auto-journal exchanges.
- `api/rest/server.go:162-269` - Route map showing how memory, embedding, agent, pipeline, governance, and org/federation capabilities are wired into one authenticated API.
- `internal/embedding/ollama.go:30-51,62-112` - Local embedding provider implementation (Ollama HTTP calls), which powers semantic recall paths used by MCP tools.

## 6. Use-Case Mapping

The assigned label `RAG + Agents` is **partly correct**: SAGE clearly implements retrieval over persisted memories (embedding query + FTS fallback) and exposes this to LLM agents (`internal/mcp/tools.go:433-513`, `647-718`). However, after reading the runtime code, the stronger classification is **Workflow Automation** for multi-agent operations: explicit task/message routing (`sage_pipe`/inbox/result), lifecycle enforcement, governance, and agent registry dominate the architecture (`api/rest/pipe_handler.go`, `internal/mcp/server.go`).

So this is best viewed as an agent memory-and-coordination platform where RAG is one capability inside a larger automation/governance workflow system.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong custom MCP implementation with practical lifecycle controls (`sage_inception`/`sage_turn` nudges and blocking).
  - Explicit multi-agent coordination primitives (provider/agent addressing, inbox claim semantics, result journaling).
  - Security-focused transport/auth (Ed25519 request signing, optional TLS/quorum support).
  - Built-in semantic + non-semantic retrieval modes, making memory recall robust to embedding availability.
  - Rich operational surface (governance, org/dept RBAC, federation) for real deployment contexts.

- **Limitations:**
  - No native in-repo LLM reasoning engine/planner; relies on external model clients to decide when/how to use tools.
  - Multi-agent collaboration is infrastructural, not autonomous team planning (no internal role-decomposition algorithm).
  - Tool instruction strings are extensive/prescriptive and may be brittle across different model behaviors.
  - Considerable system complexity (consensus, stores, RBAC, governance) raises setup and evaluation overhead.
  - Heavy emphasis on memory/governance may be overkill for simpler single-agent RAG tasks.

- **Research relevance:**
  - Good evidence for **infrastructure-centric multi-agent systems** where coordination is achieved via protocol + shared memory, not monolithic planners.
  - Useful case for studying **governed memory persistence** and consensus-backed knowledge curation in agent ecosystems.
  - Illustrates **event-driven agent collaboration** via asynchronous pipeline mailboxes.
  - Supports comparative studies of semantic retrieval vs operational governance constraints in long-running agent deployments.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
