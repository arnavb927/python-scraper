---
repo_name: ollama/ollama
url: "https://github.com/ollama/ollama"
stars: 169741
forks: 15745
contributors_count: 599
last_commit_date: "2026-04-22T23:34:19+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:12:58.058058+00:00"
model: auto
duration_s: 84.5
clone_size_kb: 94247
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`ollama/ollama` is primarily a local LLM serving/runtime project (CLI + HTTP API), but this codebase also contains an **experimental agent mode** that lets a model call tools in a loop. A user runs Ollama (server + CLI), starts interactive chat, and if the selected model supports tool calling, Ollama exposes tools like `bash` (and optionally `web_search`/`web_fetch`) to the model. The runtime executes approved tool calls, feeds results back as `tool` messages, and continues until the model stops requesting tools. In practice, users get a terminal assistant that can reason, run commands, and iterate with tool feedback under human approval controls.

## 2. Agent Framework & Architecture

This repo does **not** use LangChain, LangGraph, CrewAI, AutoGen, or LlamaIndex as core runtime frameworks. The implementation is a **custom Go agent loop** built directly on Ollama’s own chat/tool-call APIs (`x/cmd/run.go`, `x/tools/*`, `x/agent/*`, `server/routes.go`).

Architecture-wise, there are two layers:

1. **Server/tool-call parsing layer**: `ChatHandler` in `server/routes.go` parses model output into content, thinking, and tool calls (either via model-specific built-in parsers or generic parsing via `tools.NewParser(...)`) and emits those calls in API responses.
2. **CLI orchestration layer**: `Chat(...)` in `x/cmd/run.go` runs the iterative “assistant -> tool call -> tool execution -> tool result -> assistant” loop. Tool execution is mediated by a registry (`x/tools/registry.go`) and approval policy (`x/agent/approval.go`).

The “intelligence” lives mostly in the model prompt/template + model output parser behavior, while orchestration policy (approval, retries, truncation, loop continuation) lives in Go code.

## 3. Orchestration Pattern

Closest match: **sequential loop (single-agent tool-using workflow)**, not manager-worker multi-agent.

Control flow is explicit in `x/cmd/run.go`: after each model response, pending tool calls are executed, appended as `tool` messages, and the same assistant is queried again.

```260:275:x/cmd/run.go
// Agentic loop: continue until no more tool calls
for {
    req := &api.ChatRequest{
        Model:    opts.Model,
        Messages: messages,
        ...
    }
    if toolRegistry != nil {
        apiTools := toolRegistry.Tools()
        if len(apiTools) > 0 {
            req.Tools = apiTools
        }
    }
```

```350:366:x/cmd/run.go
// If no tool calls, we're done
if len(pendingToolCalls) == 0 || toolRegistry == nil {
    break
}
// Add assistant's tool call message to history
assistantMsg := api.Message{
    Role:      "assistant",
    Content:   fullResponse.String(),
    Thinking:  thinkingContent.String(),
    ToolCalls: pendingToolCalls,
}
messages = append(messages, assistantMsg)
```

Server-side parsing of tool calls is handled in `ChatHandler` before the loop consumer sees them:

```2425:2428:server/routes.go
var toolParser *tools.Parser
if len(req.Tools) > 0 && (builtinParser == nil || !builtinParser.HasToolSupport()) {
    toolParser = tools.NewParser(m.Template.Template, req.Tools)
}
```

## 4. Tools & External Integrations

- **Local shell/terminal execution (`bash`)**: wired in `x/tools/bash.go` and registered via `x/tools/registry.go` (`DefaultRegistry`, `RegisterBash`).
- **Web search API via Ollama cloud**: `x/tools/websearch.go` calls `https://ollama.com/api/web_search`, signs requests with local key (`auth.Sign`), and handles auth failures.
- **Web fetch API via Ollama cloud**: `x/tools/webfetch.go` calls `https://ollama.com/api/web_fetch`, also signed/authenticated.
- **Tool approval/safety gate**: `x/agent/approval.go` enforces deny-pattern blocking, per-session allowlist, and interactive approval UX.
- **Model inference backend (local/remote)**: `server/routes.go` `ChatHandler` and `GenerateHandler` schedule runners and can proxy to remote/cloud models (`api.NewClient(remoteURL, ...)`).
- **OpenAI Responses compatibility surface**: `openai/responses.go` maps tool/function-call structured inputs/outputs to Ollama chat messages and back.

No MCP server orchestration or vector DB/RAG store wiring is central in this agent loop path.

## 5. Notable Code Walkthrough

- `x/cmd/run.go:163-514` - Core experimental agent chat loop (`Chat`): sends chat requests with tools, collects `ToolCalls`, executes tools, appends `tool` messages, retries on failures, and repeats until no more calls.
- `x/agent/approval.go:153-193,386-478,480-543` - Approval and safety policy: deny dangerous commands, maintain exact/prefix allowlists, and request user decisions (`once/always/deny`) before tool execution.
- `x/tools/registry.go:12-131` - Tool abstraction/registry: defines tool interface, registration, JSON-schema exposure to model, and dispatcher for tool execution.
- `server/routes.go:2138-2673` - Server `ChatHandler`: prepares model prompt, handles thinking/tool parsing, emits structured `ToolCalls` in streamed/non-streamed responses.
- `openai/responses.go:404-569,751-876` - OpenAI Responses bridge: converts Responses API items (including function calls/output) into Ollama `ChatRequest`/`Message` format and serializes tool-call outputs back.

## 6. Use-Case Mapping

For the assigned `Browser / Terminal Use` label: the **terminal-use** part is strongly supported. The `bash` tool executes shell commands, and the loop can iteratively inspect files/run commands/act on outputs (`x/tools/bash.go`, `x/cmd/run.go`). The **browser-use** part is partial: web access is via hosted `web_search` and `web_fetch` HTTP tools, not full browser automation (no Playwright-style control loop in the inspected paths). Overall, the best fit is closer to **Workflow Automation** (tool-augmented command/search/fetch loops), with terminal use as a concrete modality.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Practical end-to-end tool loop in production-grade serving stack, not toy code (`x/cmd/run.go`).
  - Strong human-in-the-loop controls (approval prompts, allowlists, deny patterns) for risky tools (`x/agent/approval.go`).
  - Works across local and remote/cloud-backed models with same API surface (`server/routes.go`).
  - Good protocol interoperability (OpenAI Responses + function calling conversion) (`openai/responses.go`).
  - Clear modular tool abstraction for adding/removing tools (`x/tools/registry.go`).

- **Limitations:**
  - No true multi-agent coordination (no planner/worker/team roles); it is a single-agent sequential loop.
  - Web tools depend on Ollama-hosted endpoints/auth; not fully local/offline (`x/tools/websearch.go`, `x/tools/webfetch.go`).
  - Default toolset is intentionally narrow (bash by default; web search currently feature-gated in registry comments).
  - Bash execution has broad capability; safety relies on pattern filters and user judgment, which can be bypass-prone in principle.
  - Limited explicit long-horizon planning/state abstractions beyond message history loop.

- **Research relevance:**
  - Evidence of how agentic tool-calling is integrated into mainstream inference servers/CLI products.
  - Useful case for studying human approval UX and policy gating in LLM tool use.
  - Demonstrates protocol-level function-call interoperability between APIs and internal chat abstractions.
  - Good reference for single-agent iterative tool orchestration under real latency/error constraints.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
