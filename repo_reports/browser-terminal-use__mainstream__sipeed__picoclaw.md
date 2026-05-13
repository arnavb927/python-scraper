---
repo_name: sipeed/picoclaw
url: "https://github.com/sipeed/picoclaw"
stars: 28445
forks: 4061
contributors_count: 205
last_commit_date: "2026-04-23T02:35:50+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:33:27.385264+00:00"
model: auto
duration_s: 129.8
clone_size_kb: 36035
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`sipeed/picoclaw` is a Go-based agent runtime and deployment platform for running an AI assistant across CLI, chat channels, and a local web launcher. In practice, users run commands like `picoclaw agent` (interactive/local), `picoclaw gateway` (chat-app integrations), or `picoclaw-launcher` (browser UI) to operate the same core agent loop. The system combines LLM calls with tool execution (files, shell, web, MCP, messaging, skills) and persistent session memory so it can complete multi-step tasks. It targets lightweight, always-on automation across many environments rather than only coding use.

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework** in Go, not CrewAI/LangGraph/LangChain/AutoGen. Core orchestration types (`AgentLoop`, `Pipeline`, `turnState`) and runtime lifecycle are implemented in-house in files like `pkg/agent/agent.go:34-76`, `pkg/agent/turn_coord.go:17-246`, and `pkg/agent/pipeline_execute.go:25-728`.

Architecture-wise, there is a multi-agent registry plus per-turn execution engine. `AgentRegistry` builds multiple configured agents (`cfg.agents.list`) and can route inbound work to a specific agent instance (`pkg/agent/registry.go:14-103`). Each `AgentInstance` carries its own workspace, session store, model/fallback config, tool registry, and optional subagent policy (`pkg/agent/instance.go:22-249`).

“Intelligence” is distributed across: (1) model prompts/context assembly and memory compaction; (2) iterative LLM+tool loop control (`runTurn` + `ExecuteTools`); and (3) agent-to-agent delegation via sub-turn spawning (`pkg/agent/subturn.go:202-496`) and spawn/subagent tools (`pkg/tools/subagent.go:13-456`). So this is not just a single assistant wrapper; it includes explicit runtime coordination primitives for multiple agents/subagents.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with iterative tool-loop turns**.

- Parent turn executes an LLM/tool loop and can spawn child sub-turns with depth/concurrency limits (`pkg/agent/subturn.go:271-315`, `328-395`, `466-495`).
- Child results are fed back into the parent turn via pending results channels and injected as new context (`pkg/agent/turn_coord.go:109-121`, `195-223`).

Example control flow excerpt (`pkg/agent/turn_coord.go:165-199`):

```go
ctrl, callErr := pipeline.CallLLM(ctx, turnCtx, ts, exec, iteration)
...
switch ctrl {
case ControlContinue:
    continue
case ControlBreak:
    return pipeline.Finalize(...)
case ControlToolLoop:
    toolCtrl := pipeline.ExecuteTools(...)
```

Example parent->child delegation (`pkg/agent/subturn.go:466-479`):

```go
turnRes, turnErr := al.runTurn(childCtx, childTS, pipeline)
if semAcquired {
    <-parentTS.concurrencySem
    semAcquired = false
}
if turnErr != nil { ... } else { ... }
```

## 4. Tools & External Integrations

- **Filesystem + editing tools** (`read_file`, `write_file`, `edit_file`, `append_file`, `list_dir`) wired per-agent in `pkg/agent/instance.go:87-119` via `pkg/tools/fs_facade.go:10-100`.
- **Terminal/shell execution** via `exec` tool (sync/background/PTy/session management), with safety guardrails, in `pkg/tools/shell.go:37-47`, `184-262`, `264-353`.
- **Web search + web fetch** integrations (Brave, Tavily, DuckDuckGo, Perplexity, SearXNG, GLM Search, Baidu; plus SSRF-aware fetch) in `pkg/tools/integration/web.go:99-1092`, `1492-1840`.
- **MCP servers/tools** loaded dynamically and registered into agent tool registries in `pkg/agent/agent_mcp.go:76-247`.
- **Messaging/channel actions** (`message`, `reaction`, file/media send) wired in `pkg/agent/agent_init.go:145-201`.
- **Skills ecosystem** (search/install skill registries) in `pkg/agent/agent_init.go:218-236`.
- **Subagent orchestration tools** (`spawn`, `spawn_status`, `subagent`) wired through a shared `SubagentManager` and `SubTurnSpawner` in `pkg/agent/agent_init.go:238-339`, `pkg/tools/subagent.go:56-165`, `337-456`.
- **Many LLM/provider backends** configured in model config + provider factory (`go.mod` dependencies and creation path in `pkg/agent/instance.go:186-223`).

## 5. Notable Code Walkthrough

- `pkg/agent/turn_coord.go:17-246` - Core turn coordinator: runs iterative LLM/tool loop, handles aborts, steering injection, and sub-turn result ingestion; this is the main runtime state machine.
- `pkg/agent/subturn.go:202-585` - Implements hierarchical child-agent execution with depth/concurrency/time budget controls and async result delivery back to parent.
- `pkg/agent/agent_init.go:24-341` - Bootstraps `AgentLoop`, fallback chains, hooks/events, and registers all shared tools (web, MCP-adjacent, messaging, spawn/subagent stack).
- `pkg/agent/agent_mcp.go:76-247` - MCP integration layer: loads configured servers, registers MCP tools across agents, and optionally enables discovery tooling.
- `pkg/tools/subagent.go:56-456` - Defines subagent task manager and synchronous `subagent` tool, including fallback legacy tool-loop execution path.

## 6. Use-Case Mapping

This repo **partly** supports Browser/Terminal Use (notably the `exec` terminal tool and `web_fetch`/`web_search` tools), but its core implementation is broader: it is a general-purpose multi-channel automation agent runtime with scheduled tasks, chat-channel integrations, skills, and MCP extensibility. Based on code, the better primary category is **Workflow Automation**, because the architecture is centered on orchestrating actions across tools/channels rather than browser automation specifically. So the upstream “Browser / Terminal Use” label is directionally related but too narrow.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Custom, production-style multi-agent runtime with explicit parent/child coordination and backpressure (`subturn` depth/concurrency control).
  - Strong tooling surface (FS, shell, web, MCP, skills, messaging) unified in one loop.
  - Safety-aware implementation for high-risk tools (exec deny patterns/workspace checks; web-fetch SSRF/DNS-rebinding defenses).
  - Multi-agent configurability via registry + per-agent workspaces/models/subagent policies.
  - Event/hook architecture for observability and runtime interception.

- **Limitations:**
  - Complexity is high; orchestration behavior spans many files and internal states, raising maintenance/debugging burden.
  - Hierarchical delegation exists, but fewer explicit peer-to-peer/swarm coordination primitives are visible.
  - Some backward-compatibility/legacy paths (e.g., fallback subagent tool loop) suggest dual behavior modes.
  - Safety policies are regex/config driven; correctness depends on robust config and continual hardening.
  - Browser automation is not first-class in core runtime (relative to terminal/web-fetch/search style tools).

- **Research relevance:**
  - Useful evidence of a practical **hierarchical MAS** pattern (parent turn + child sub-turns) in a lightweight systems language.
  - Demonstrates integrated study surface for **tool-augmented agents** with real-world safety controls.
  - Shows how **MCP-based dynamic capability injection** can be merged into a long-running agent runtime.
  - Illustrates engineering trade-offs between flexible runtime orchestration and strict operational safeguards.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
