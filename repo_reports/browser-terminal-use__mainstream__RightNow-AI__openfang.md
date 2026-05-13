---
repo_name: RightNow-AI/openfang
url: "https://github.com/RightNow-AI/openfang"
stars: 16912
forks: 2144
contributors_count: 65
last_commit_date: "2026-04-19T19:57:55+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 10
architecture_labels: [LangGraph, LangChain, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-05-05T06:18:37.633464+00:00"
model: auto
duration_s: 86.3
clone_size_kb: 21080
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`openfang` is a Rust-based “agent operating system” that runs as a local daemon (`openfang start`) with an HTTP API and dashboard, where users can spawn named agents from TOML manifests and message them at runtime. Under the hood, each agent runs an LLM tool-use loop with memory, policy gates, quotas, and optional scheduling/background execution (`crates/openfang-kernel/src/kernel.rs:1652-1773`, `crates/openfang-runtime/src/agent_loop.rs:261-272`). Users get a platform for orchestrating many specialized agents, wiring them into workflows, channels, and external protocols rather than a single chatbot. The codebase is multi-crate and includes runtime, kernel, API, memory, channels, skills, and networking layers (`Cargo.toml:1-18`).

## 2. Agent Framework & Architecture

The core framework is **custom** (Rust-native), not LangGraph/LangChain/AutoGen/CrewAI at runtime. The workspace dependencies show no LangChain/LangGraph crates (`Cargo.toml:27-170`), and the core orchestration is implemented in OpenFang’s own kernel/runtime (`openfang-kernel`, `openfang-runtime`). There is an optional external example agent folder using Python LangChain, but it is not the main runtime engine (`agents/langchain-code-reviewer/*`).

Architecture-wise, `OpenFangKernel` is the control plane that owns registry, scheduler, workflow engine, triggers, memory, tool catalogs, MCP connections, A2A stores, and browser/web contexts (`crates/openfang-kernel/src/kernel.rs:60-183`). When a message arrives, the kernel dispatches by module type (WASM/Python/LLM), with default `builtin:chat` going into the LLM loop (`crates/openfang-kernel/src/kernel.rs:1755-1763`). Intelligence lives in (a) per-agent system prompts and prompt-builder context composition, and (b) the iterative tool-use loop (`crates/openfang-kernel/src/kernel.rs:2591-2673`, `crates/openfang-runtime/src/agent_loop.rs:455-463`).

This is materially multi-agent: agents can message other agents, spawn subagents, post/claim tasks, and be chained by declarative workflows (`crates/openfang-runtime/src/tool_runner.rs:297-317`, `crates/openfang-kernel/src/workflow.rs:66-132`).

## 3. Orchestration Pattern

Closest match: **hierarchical + workflow graph hybrid**.

- **Manager-worker/hierarchical:** one agent can invoke `agent_send`/`agent_spawn` tools to delegate work to other agents (`crates/openfang-runtime/src/tool_runner.rs:1627-1668`).
- **Graph/pipeline orchestration:** Workflow engine supports sequential, fan-out/collect, conditional, and loop step modes (`crates/openfang-kernel/src/workflow.rs:117-132`, `crates/openfang-kernel/src/workflow.rs:482-785`).

Control-flow excerpts:

```4048:4097:crates/openfang-kernel/src/kernel.rs
pub async fn run_workflow(...) -> KernelResult<(WorkflowRunId, String)> {
    ...
    let send_message = |agent_id: AgentId, message: String| async move {
        self.send_message(agent_id, &message).await.map(|r| (r.response, ...))
    };
    let output = tokio::time::timeout(..., self.workflows.execute_run(run_id, resolver, send_message)).await?;
}
```

```1627:1653:crates/openfang-runtime/src/tool_runner.rs
async fn tool_agent_send(...) -> Result<String, String> {
    ...
    if current_depth >= MAX_AGENT_CALL_DEPTH { return Err(...); }
    AGENT_CALL_DEPTH.scope(std::cell::Cell::new(current_depth + 1), async {
        kh.send_to_agent(agent_id, message).await
    }).await
}
```

## 4. Tools & External Integrations

- **LLM providers (OpenAI/Anthropic/Groq/Gemini/Bedrock/etc.)** via driver layer; kernel resolves provider/model and runs completion loop (`crates/openfang-kernel/src/kernel.rs:23-25`, `crates/openfang-kernel/src/kernel.rs:2730-2782`, `crates/openfang-runtime/src/drivers/*`).
- **MCP servers** (stdio/SSE/HTTP transports) with namespaced MCP tools (`mcp_{server}_{tool}`), discovered and called at runtime (`crates/openfang-runtime/src/mcp.rs:1-9`, `crates/openfang-runtime/src/mcp.rs:91-157`, `crates/openfang-runtime/src/mcp.rs:160-201`).
- **Browser automation** through native CDP (Chromium websocket control), exposed as `browser_*` tools (`crates/openfang-runtime/src/browser.rs:1-11`, `crates/openfang-runtime/src/tool_runner.rs:378-472`).
- **Terminal/subprocess control** via `shell_exec`, `process_start/poll/write/kill`, with policy and taint checks (`crates/openfang-runtime/src/tool_runner.rs:243-295`, `crates/openfang-runtime/src/tool_runner.rs:1200-1250`).
- **Web search/fetch** with web context and SSRF/taint protections (`crates/openfang-runtime/src/tool_runner.rs:210-239`, `crates/openfang-runtime/src/web_search.rs`, `crates/openfang-runtime/src/web_fetch.rs`).
- **Agent-to-agent protocol (A2A)** for external agent discovery/task exchange (`crates/openfang-runtime/src/a2a.rs:1-11`, `crates/openfang-api/src/routes.rs:6657-6766`).
- **Channel integrations** (Telegram/Discord/Slack/etc.) routed through adapters, enabling agents to operate over messaging platforms (`crates/openfang-channels/src/*`, `crates/openfang-api/src/server.rs:41-43`).

## 5. Notable Code Walkthrough

- `crates/openfang-runtime/src/agent_loop.rs:261-1000` - Core iterative LLM loop: message assembly, loop-guard checks, tool-use handling, timeout/hook integration, and stop-reason-driven continuation. This is the execution heart of each LLM agent turn.
- `crates/openfang-runtime/src/tool_runner.rs:109-470` - Central tool dispatcher for filesystem, web, shell, browser, memory, scheduling, and inter-agent calls; enforces capabilities and approval policy before execution.
- `crates/openfang-kernel/src/kernel.rs:1652-1773` - Message ingress path and module dispatch (WASM/Python/LLM), plus per-agent locking/quota checks. It turns API/trigger/channel events into concrete agent execution.
- `crates/openfang-kernel/src/workflow.rs:66-132,430-797` - Declarative multi-step orchestration engine with sequential/fan-out/collect/conditional/loop semantics and per-step error policies.
- `crates/openfang-runtime/src/mcp.rs:91-201` - MCP client implementation: connect, discover tool schemas, namespace tool names, and execute remote MCP calls.

## 6. Use-Case Mapping

This repo does support **Browser / Terminal Use** through first-class `browser_*` and `shell_exec/process_*` tools (`crates/openfang-runtime/src/tool_runner.rs:378-472`, `crates/openfang-runtime/src/tool_runner.rs:243-295`). However, after reading the code, the broader primary pattern is **Workflow Automation**: multi-agent workflow definitions, scheduled/background agents, triggers, task queues, and channel bridges are all core platform features (`crates/openfang-kernel/src/workflow.rs:1-11`, `crates/openfang-kernel/src/kernel.rs:4154-4227`, `crates/openfang-types/src/agent.rs:225-241`). So the assigned label is partially right but narrower than the implemented scope.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong built-in multi-agent orchestration primitives (workflows + inter-agent delegation + task tools).
  - Broad tool surface with explicit capability gating and approval hooks (`tool_runner` policy path).
  - Real systems integration: MCP, A2A, channels, browser CDP, process manager.
  - Production-style controls: quotas, audit logs, retries/timeouts, supervisor health.
  - Modular architecture across crates; clear separation of kernel/runtime/api/types.

- **Limitations:**
  - Very large monolithic files (`agent_loop.rs`, `tool_runner.rs`, `kernel.rs`) raise maintenance and verification complexity.
  - Some orchestration decisions are prompt-driven and may be non-deterministic without stricter planner semantics.
  - In-memory stores (e.g., some task/trigger state patterns) can limit durability depending on subsystem.
  - Security model is extensive but operationally complex (multiple gates, modes, policies) and easy to misconfigure.
  - External LangChain labeling can mislead; core runtime is custom, so ecosystem interoperability patterns are bespoke.

- **Research relevance:**
  - Evidence of a practical multi-agent OS architecture combining autonomous loops with explicit workflow orchestration.
  - Example of layered governance in agent systems: capability allowlists, human approval, taint/SSRF checks.
  - Useful case for studying hybrid coordination (tool-mediated delegation + pipeline graph execution).
  - Demonstrates integration-centric MAS design (A2A + MCP + channel adapters) in a production-grade codebase.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
