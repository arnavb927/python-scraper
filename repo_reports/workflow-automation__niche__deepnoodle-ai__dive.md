---
repo_name: deepnoodle-ai/dive
url: "https://github.com/deepnoodle-ai/dive"
stars: 122
forks: 16
contributors_count: 5
last_commit_date: "2026-04-12T19:17:20+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 1
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T18:08:07.450423+00:00"
model: auto
duration_s: 72.8
clone_size_kb: 5450
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`deepnoodle-ai/dive` is a Go library for building tool-using LLM agents, plus an experimental Claude-Code-style CLI in `experimental/cmd/dive`. A developer instantiates `dive.Agent` with a model, system prompt, tools, and optional hooks/sessions, then calls `CreateResponse` to run a full tool-call loop until completion or suspension. The runtime handles streaming events, retries across tool iterations, session persistence, and suspend/resume for human-in-the-loop workflows. In practice, users either embed this in backend services or run the experimental CLI to automate coding/workflow tasks with filesystem, shell, and web tools.

## 2. Agent Framework & Architecture

This is a **custom agent framework** (not LangChain/LangGraph/CrewAI/AutoGen). The core abstractions are native Go interfaces (`Agent`, `Tool`, `Session`, `Hooks`, `llm.LLM`) and a custom loop in `agent.go` (`CreateResponse` + `generate`) that repeatedly calls the model, executes returned tool calls, and feeds `tool_result` messages back to the model (`agent.go:1292-1455`).

The architecture is library-first: `NewAgent` composes static tools, dynamic toolsets, extensions, and lifecycle hooks (`agent.go:175-239`). “Intelligence” is split between user-supplied system prompts and model outputs (tool_use blocks), while control logic is deterministic in code: pre/post hooks, iteration limits, tool execution policy (sequential/parallel), and stop hooks (`agent.go:49-77`, `agent.go:1490-1772`).

The repo also includes optional multi-agent capabilities under `experimental/`: subagent definitions/registry (`experimental/subagent/subagent.go:48-194`), a `Task` tool that spawns child `dive.Agent` instances (`experimental/toolkit/extended/task.go:174-451`), and A2A bridges for remote agent-to-agent interaction (`experimental/a2alib/executor.go:22-170`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)** with a sequential inner loop.

- The main agent runs a sequential iterative loop: LLM response -> tool calls -> tool results -> next LLM call (`agent.go:1318-1448`).
- When the `Task` tool is invoked, it creates/uses a specialized subagent and delegates a subtask, then returns output/status to the parent (`experimental/toolkit/extended/task.go:319-327`, `experimental/toolkit/extended/task.go:374-411`).

Control-flow excerpt (core loop):
```1304:1417:agent.go
collectingCallback := func(ctx context.Context, item *ResponseItem) error {
    items = append(items, item)
    return callback(ctx, item)
}
...
toolCalls := response.ToolCalls()
if len(toolCalls) == 0 {
    break
}
batch, err := a.executeToolCalls(ctx, hctx, toolCalls, toolsByName, collectingCallback)
...
toolResultMessage = llm.NewToolResultMessage(getToolResultContent(completedResults)...)
newMessage(toolResultMessage)
```

Control-flow excerpt (manager spawning worker):
```319:327:experimental/toolkit/extended/task.go
agent, err := t.agentFactory(ctx, input.SubagentType, def, t.parentTools)
if err != nil {
    return dive.NewToolResultError(fmt.Sprintf("failed to create agent: %s", err.Error())), nil
}
taskID := fmt.Sprintf("task_%s", uuid.New().String()[:8])
return t.executeTask(ctx, input, agent, taskID)
```

## 4. Tools & External Integrations

- **Local filesystem + shell tools** (`ReadFile`, `Write`, `Edit`, `Glob`, `Grep`, `ListDirectory`, `Bash`) wired in CLI tool factory: `experimental/cmd/dive/main.go:910-944`.
- **Interactive human input tool** (`AskUser`) wired with TUI dialog routing: `experimental/cmd/dive/main.go:941-944`, dialog handlers `main.go:600-783`.
- **Web fetch/search integrations** via Firecrawl/HTTP fetcher and Kagi/Google search fallback: `experimental/cmd/dive/main.go:946-966`.
- **Image/video generation tools** selected by provider env availability: `experimental/cmd/dive/main.go:968-980`, defaults `main.go:1011-1035`.
- **MCP (Model Context Protocol)** client manager for discovering external MCP tools and adapting them into Dive tools: `experimental/mcp/manager.go:45-131`.
- **A2A (Agent-to-Agent protocol)** integration to expose Dive agents as remote agents and resume suspended turns over A2A tasks: `experimental/a2alib/executor.go:55-170`, `executor.go:281-320`.
- **Multi-provider LLM backends** (Anthropic/OpenAI/Google/Grok/OpenRouter/Mistral/Ollama) are first-class in provider packages and model selection logic (`README.md:122-125`, `experimental/cmd/dive/main.go:1037-1054`).

## 5. Notable Code Walkthrough

- `agent.go:312-670` - Main `CreateResponse` orchestration: session loading, hooks, generation loop invocation, suspend/resume handling, and persistence semantics.
- `agent.go:1292-1772` - Core runtime loop and tool execution engine, including sequential vs parallel tool calls and callback/event emission.
- `experimental/toolkit/extended/task.go:174-451` - `Task` tool implementing parent-to-subagent delegation, async/background execution, and resumable subagent task records.
- `experimental/cmd/dive/main.go:164-376` - CLI composition root: builds tools, permission hooks, subagent/task registries, skills extension, and creates the primary agent.
- `experimental/a2alib/executor.go:55-170` - A2A executor bridge mapping A2A events/messages onto `Agent.CreateResponse`, enabling remote multi-turn agent execution and streaming status.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. The code is centered on automating multi-step operational workflows: inspect files, run commands, fetch/search web data, optionally delegate subtasks to specialized subagents, then synthesize output through an iterative tool-using loop (`agent.go:1318-1448`, `experimental/cmd/dive/main.go:910-983`, `experimental/toolkit/extended/task.go:204-214`). Suspend/resume support also enables real-world interrupted workflows that require external input/approval before continuation (`agent.go:672-789`, `response.go:120-185`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Robust agent loop with explicit hook points and strong lifecycle control (`agent.go:49-77`, `agent.go:530-623`).
  - Production-grade suspend/resume state model for human-in-the-loop and async tool completion (`agent.go:791-1133`, `response.go:120-185`).
  - Practical multi-agent delegation via `Task` tool with subagent registry and background execution (`experimental/toolkit/extended/task.go:174-451`).
  - Broad integration surface (local tools, web, MCP, A2A, multimodal content) in one framework (`main.go:910-983`, `experimental/mcp/manager.go:45-131`, `experimental/a2alib/executor.go:22-53`).

- **Limitations:**
  - Multi-agent coordination is mostly in `experimental/`; stable core remains primarily single-agent + tools.
  - No explicit graph/state-machine planner abstraction (e.g., node/edge DAG orchestration); orchestration is loop + tool call semantics.
  - Subagent model override enum (`sonnet|opus|haiku`) is narrow and provider-specific in `Task` schema (`experimental/toolkit/extended/task.go:245-249`).
  - MCP tool naming conflict handling is simplistic (duplicate-name error instead of namespace strategy) (`experimental/mcp/manager.go:97-106`).

- **Research relevance:**
  - Evidence for **hierarchical agent delegation** in practical coding/workflow assistants (manager invoking specialized worker agents).
  - Useful case study of **agent suspension/resumption protocols** and partial tool-result reconciliation in long-running tasks.
  - Demonstrates **tool-centric agent architecture** as an alternative to explicit graph frameworks.
  - Shows emerging **inter-agent interoperability** via A2A and MCP in a single Go agent stack.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
