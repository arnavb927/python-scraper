---
repo_name: Kocoro-lab/ShanClaw
url: "https://github.com/Kocoro-lab/ShanClaw"
stars: 233
forks: 106
contributors_count: 7
last_commit_date: "2026-04-23T02:46:25+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:41:18.830650+00:00"
model: auto
duration_s: 98.8
clone_size_kb: 14123
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

ShanClaw is a Go-based runtime (`shan` CLI + daemon) for running tool-using AI agents locally while optionally delegating larger workflows to Shannon Cloud. A user can run one-shot commands, use an interactive TUI, or run `shan daemon` to process channel messages (Slack/LINE/etc.) through the same agent loop. The core behavior is: build prompt + tool schemas, call an LLM, execute returned tool calls (filesystem/shell/browser/MCP/etc.), then iterate until a final answer. It solves “agent execution infrastructure” more than “one fixed app”: session persistence, approval gates, tool routing, retries, and cloud delegation are all first-class runtime concerns. The output is a working assistant that can perform local terminal/browser automation and multi-step workflow execution with audit/session tracking.

## 2. Agent Framework & Architecture

This repo does **not** use LangChain/LangGraph/CrewAI/AutoGen as its runtime framework; it is a **custom agent framework in Go**. The core abstractions are internal: `AgentLoop`, `Tool`, `ToolRegistry`, and an `LLMClient` interface implemented by `GatewayClient` and `OllamaClient` (`internal/agent/loop.go:884+`, `internal/agent/tools.go:132-136`, `internal/client/llmclient.go:5-10`).

High-level architecture: one primary orchestrator loop per request (`AgentLoop.Run`) executes iterative LLM-tool turns with compaction, loop detection, watchdog, retries, and permission checks (`internal/agent/loop.go:884-1130`, `1580+`, `2928+`). In daemon mode, `RunAgent` wraps that loop with routing/session management, source-aware output formatting, and event-bus emission (`internal/daemon/runner.go:495-1268`). Tools are layered local > MCP > gateway, with dynamic registration and filtering (`internal/tools/register.go:20-83`, `212-297`, `327-348`).

Multi-agent behavior exists via cloud delegation: local agent can call `cloud_delegate`, submitting a remote `research`/`swarm` workflow and streaming back sub-agent outputs (`internal/tools/cloud_delegate.go:67-110`, `153-176`, `198-214`; `internal/client/gateway.go:586-608`, `761-795`).

## 3. Orchestration Pattern

Closest fit: **hierarchical manager-worker + event-driven**.

- Local run is manager-style: one controller agent decides when to call tools and how to continue.
- `cloud_delegate` acts as escalation to remote worker graph/swarm workflows.
- Daemon transport and progress are event-driven over WebSocket/SSE.

Control flow excerpt (iterative manager loop):

```1580:1587:internal/agent/loop.go
for i := 0; ; i++ {
    effectiveMax := a.effectiveMaxIter(toolsUsed)
    if i >= effectiveMax {
        break
    }
    iterationCount = i + 1
```

Tool execution orchestration excerpt (partitioned batch execution):

```2501:2504:internal/agent/loop.go
batches := partitionToolCalls(approved)
a.tracker.Enter(PhaseExecutingTools)
executeBatches(ctx, batches, execResults, readTracker, a.handler)
a.tracker.MarkDirty()
```

Delegation control excerpt (manager -> remote workflow):

```153:167:internal/tools/cloud_delegate.go
taskReq := client.TaskRequest{
    Query:   args.Task,
    Context: taskContext,
}
resp, err := t.gw.SubmitTaskStream(timeoutCtx, taskReq)
```

## 4. Tools & External Integrations

- **Local system tools** (file read/write/edit, glob/grep, bash, process, HTTP, clipboard, GUI automation) are registered in `RegisterLocalTools` (`internal/tools/register.go:31-67`).
- **Browser automation** via local browser/computer tools and via Playwright MCP; legacy browser tools are disabled when Playwright MCP is present (`internal/tools/register.go:257-271`).
- **MCP servers** (stdio/http) are connected dynamically with tool discovery via `ClientManager.ConnectAll` (`internal/mcp/client.go:22-32`, `75-124`).
- **Shannon Gateway LLM API** for completions and streaming (`/v1/completions`) (`internal/client/gateway.go:628-664`, `671-759`).
- **Gateway server-side tools** fetched from `/api/v1/tools` and selectively exposed (`internal/client/gateway.go:938-963`; `internal/tools/register.go:162-187`).
- **Cloud multi-agent workflows** (`research`/`swarm`) via task submission + SSE stream (`internal/client/gateway.go:586-608`, `761-795`; `internal/tools/cloud_delegate.go:99-106`, `198-214`).
- **Session store + search index** in SQLite FTS5 (`internal/session/index.go:30-58`, `88-99`).
- **Memory sidecar integration** with fallback behavior (`internal/tools/memory.go:31-38`, `109-139`).
- **WebSocket daemon/cloud transport** with claim/progress/reply/event message protocol (`internal/daemon/client.go:16-35`, `100-118`, `138-149`, `211-239`).

## 5. Notable Code Walkthrough

- `internal/agent/loop.go:884-1130,1580-1660,2466-2538,2928-2962`  
  Core agent runtime: constructs prompt/tool schema context, runs iterative LLM turns, partitions tool calls for batched execution, and applies retry/backoff for transient model failures.

- `internal/daemon/runner.go:495-611,850-925,997-1046,1081-1133`  
  Production execution wrapper: resolves agent/session route, applies per-run registry + skills/memory wiring, injects runtime metadata, executes loop, and persists/streams results.

- `internal/tools/register.go:20-83,212-297,327-348,502-556`  
  Tool composition hub: registers local tools, connects MCP and gateway tools, enforces source priority, and rebuilds registries from health states.

- `internal/tools/cloud_delegate.go:65-115,117-176,198-220`  
  Bridge from local single-agent loop to remote multi-agent workflows (`research`/`swarm`) with streamed result handling and optional terminal passthrough behavior.

- `internal/client/gateway.go:480-505,628-664,671-759,761-829`  
  Client protocol layer for LLM completions, streaming deltas, task workflow submission, and task retrieval; this is where model/runtime API boundaries are concretely defined.

## 6. Use-Case Mapping

For the assigned primary use case (`Browser / Terminal Use`), the classification is partially correct: the repo clearly supports shell/filesystem automation and browser/GUI tooling (`internal/tools/register.go:31-67`, `257-271`). However, reading the orchestration code shows a broader and arguably primary emphasis on **workflow execution runtime**: daemon routing, channel ingestion, cloud delegation (`research`/`swarm`), persistence, approvals, and evented status transport (`internal/daemon/runner.go`, `internal/daemon/client.go`, `internal/tools/cloud_delegate.go`). So a better top-level category is **Workflow Automation**, with Browser/Terminal Use as an important capability subset.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong production orchestration layer (sessions, routing keys, persistence checkpoints, failure-classified run status) in `internal/daemon/runner.go`.
  - Rich heterogeneous tool stack (local, MCP, gateway, cloud delegate) with explicit priority and filtering (`internal/tools/register.go`).
  - Practical reliability engineering: loop detection, retry logic, watchdog idle handling, and partial-result semantics (`internal/agent/loop.go`).
  - Clear extension seams (`Tool`, `LLMClient`, registry rebuild paths) enabling backend/tool substitution.
  - Supports both local autonomy and remote multi-agent escalation (`cloud_delegate`).

- **Limitations:**
  - Local runtime is primarily single-agent; true multi-agent coordination is outsourced to cloud workflows rather than explicit in-process agent teams.
  - Considerable architectural complexity; behavior is spread across many layers (loop, daemon, tools, transport), increasing reasoning/debug cost.
  - Heavy reliance on proprietary gateway/cloud semantics for full capability (task workflows, server tools).
  - Some capability is platform-biased (macOS automation pathways), though not exclusively.
  - Prompt/control logic is sophisticated but largely code-embedded rather than declarative graph specs, making formal verification harder.

- **Research relevance:**
  - Good real-world evidence for **agent runtime engineering** (safety gates, loop control, checkpointing) rather than just prompting.
  - Useful case of **hybrid orchestration**: local tool-using agent with optional cloud multi-agent delegation.
  - Demonstrates practical **tool ecosystem integration** (MCP + native tools + remote API tools) in one runtime.
  - Relevant for studies on **event-driven agent operations** in production channels (WS/SSE progress + approval loops).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
