---
repo_name: j3ssie/osmedeus
url: "https://github.com/j3ssie/osmedeus"
stars: 6206
forks: 978
contributors_count: 4
last_commit_date: "2026-04-15T14:12:07+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T12:07:02.720237+00:00"
model: auto
duration_s: 80.7
clone_size_kb: 35856
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`osmedeus` is a Go-based security orchestration engine where users run YAML workflows via commands like `osmedeus run -m <module> -t <target>` and get automated reconnaissance/scanning outputs plus exported artifacts and structured step results. Beyond classic bash/function/http steps, it includes multiple LLM-capable step types (`llm`, `agent`, `agent-acp`, `agent-sdk`) embedded directly in the workflow runtime (`internal/core/types.go:20-31`). In practice, users can define an “orchestrator” agent that plans, calls tools, delegates to sub-agents, and writes outputs back into the same workflow variable/export pipeline (`internal/executor/agent_executor.go:93-387`). The project solves end-to-end workflow automation for security operations, with AI agents as programmable steps rather than a standalone chatbot.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen as its primary runtime framework. The main agent loop is **custom** Go code in `internal/executor/agent_executor.go` (iterative chat+tool loop, stop conditions, memory windowing, structured output). It also supports two additional agent backends: ACP subprocess agents (`internal/executor/acp_executor.go`) and a third-party agnostic SDK wrapper (`github.com/j3ssie/go-agent-agnostic`) in `internal/executor/sdk_executor.go:9-12`.

Architecture-wise, agent behavior is defined in workflow `Step` fields (`query`, `agent_tools`, `sub_agents`, `max_iterations`, hooks, memory) inside core types (`internal/core/step.go:235-376`, `internal/core/agent_types.go:47-62`). At runtime, `StepDispatcher` routes `type: agent` to `AgentExecutor` and `type: agent-acp` / `agent-sdk` to their dedicated executors (`internal/executor/dispatcher.go:115-126`). The “intelligence” lives in three places: LLM prompt/messages, tool schema resolution, and orchestration logic (iteration loop + tool execution + optional sub-agent spawn) (`internal/executor/agent_executor.go:132-165`, `internal/core/agent_tool_presets.go:333-422`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)** with optional parallel tool execution.

A parent agent can call `spawn_agent`, which dispatches to a named sub-agent definition and runs a child `AgentExecutor` with depth limits (`internal/executor/tool_executor.go:133-213`). This is explicit manager-worker delegation, not peer-to-peer swarm.

Short control-flow excerpts:

From tool registry wiring (`internal/executor/tool_executor.go:242-274`):
```go
// ... truncated ...
if len(subAgents) > 0 {
    // Build name → def map
    saMap := make(map[string]core.SubAgentDef, len(subAgents))
    for _, sa := range subAgents {
        saMap[sa.Name] = sa
    }
    reg.Register(&SubAgentToolExecutor{ subAgents: saMap, ... })
}
```

From sub-agent execution (`internal/executor/tool_executor.go:183-193`):
```go
syntheticStep := buildSyntheticStep(&saDef, query)
childExec := NewAgentExecutor(e.templateEngine, e.funcRegistry)
childExec.SetDepthContext(childDepth, e.maxDepth)
result, err := childExec.Execute(ctx, syntheticStep, execCtx)
```

There is also intra-iteration parallelism for multiple tool calls when enabled (`internal/executor/agent_executor.go:652-792`), but delegation topology remains hierarchical.

## 4. Tools & External Integrations

- **Filesystem + shell + grep/glob tools** (preset tools exposed to agents): `bash`, `read_file`, `save_content`, `glob`, `grep_*`, etc., defined in `internal/core/agent_tool_presets.go:17-313` and executed via function registry bridge in `internal/executor/agent_executor.go:938-990` / `internal/executor/tool_executor.go:73-110`.
- **HTTP integrations**: `http_get`/`http_request` preset tools (`internal/core/agent_tool_presets.go:164-201`), plus OpenAI-compatible LLM HTTP calls in `internal/executor/llm_executor.go:539-614`.
- **Workflow self-invocation tools**: `run_module` and `run_flow` as callable agent tools (`internal/core/agent_tool_presets.go:271-312`).
- **ACP agent subprocess integration**: built-in external agents (`claude-code`, `codex`, `opencode`, `gemini`) launched via commands (`internal/executor/acp_executor.go:31-37`, `202-225`).
- **ACP protocol sessioning**: uses `acp-go-sdk` connection/session/prompt APIs (`internal/executor/acp_executor.go:18`, `289-352`).
- **MCP servers**: ACP session is created with an empty MCP server list (`McpServers: []acp.McpServer{}`), so no active MCP server integration is wired by default (`internal/executor/acp_executor.go:330-333`).
- **Agent SDK abstraction**: optional `go-agent-agnostic` backend supports multi-agent strategy (`first`/`all`) across Claude/Codex/OpenCode adapters (`internal/executor/sdk_executor.go:9-12`, `191-237`).

## 5. Notable Code Walkthrough

- `internal/executor/agent_executor.go:93-387` - Core custom agent loop: validates step config, resolves tools, iterates LLM calls, executes tool calls, applies stop condition/memory policy, and exports agent outputs/tokens.
- `internal/executor/tool_executor.go:133-277` - Implements `spawn_agent` delegation, depth limiting, synthetic child-step construction, and parent-child token accounting; this is the core multi-agent coordination path.
- `internal/core/agent_tool_presets.go:365-422` - Dynamically injects `spawn_agent` into the LLM tool schema when sub-agents are configured, enabling controlled delegation options.
- `internal/executor/acp_executor.go:31-37,183-374` - Runs external coding agents as ACP subprocesses, initializes protocol session, sends prompt, and captures streamed/stdout output for workflow exports.
- `internal/executor/sdk_executor.go:68-85,191-237` - Provides alternate multi-agent orchestration using `go-agent-agnostic`, including “first successful” and “run all and merge outputs” strategies.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is correct. The repo’s primary unit is a YAML workflow/module composed of typed steps, and agentic components are embedded as step executors inside the same pipeline (`internal/core/step.go:177-283`, `internal/executor/dispatcher.go:141-176`). Agent outputs are exported back into workflow variables and can drive downstream non-agent automation (`internal/executor/agent_executor.go:354-380`). Even when multi-agent is used, it serves orchestration tasks (delegated recon/scanning/planning) inside larger operational workflows rather than standalone chat/productivity tooling.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Custom, inspectable agent loop with deterministic controls (`max_iterations`, stop conditions, memory truncation/summarization) (`internal/executor/agent_executor.go:215-307`, `1071-1174`).
  - Native hierarchical sub-agent delegation with explicit depth caps, reducing runaway recursion risk (`internal/executor/tool_executor.go:171-175`).
  - Rich tool surface integrated with workflow engine (shell/files/http/run-flow), enabling practical autonomous task execution (`internal/core/agent_tool_presets.go:17-313`).
  - Multiple agent backends (direct LLM API, ACP subprocess, agnostic SDK) in one execution model (`internal/executor/dispatcher.go:122-126`).

- **Limitations:**
  - No built-in long-lived multi-agent graph/state-machine orchestration beyond recursive spawn and loop iterations (no LangGraph-style explicit graph runtime observed).
  - ACP handler/API currently serializes to one subprocess at a time via mutex, limiting concurrent agent service throughput (`pkg/server/handlers/agent_chat.go:44-97`).
  - MCP integration path is present in ACP session creation but not actually populated (`internal/executor/acp_executor.go:330-333`).
  - Tool execution safety depends heavily on workflow/tool configuration (e.g., `bash` availability), with limited policy isolation in the core custom-agent path.

- **Research relevance:**
  - Good evidence of **pragmatic hierarchical MAS** in production-oriented workflow automation (parent orchestration + specialized sub-agents).
  - Useful case study for **hybrid orchestration layers**: custom internal loop plus external ACP/SDK agents.
  - Demonstrates **agent-tool co-design** where tool schemas, execution hooks, and workflow exports are tightly integrated for operational pipelines.
  - Relevant for studying **control mechanisms** (depth limits, iteration bounds, provider/model fallback, memory window summarization) in real agent systems.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
