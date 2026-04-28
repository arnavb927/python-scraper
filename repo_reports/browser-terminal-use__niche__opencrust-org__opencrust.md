---
repo_name: opencrust-org/opencrust
url: "https://github.com/opencrust-org/opencrust"
stars: 111
forks: 18
contributors_count: 7
last_commit_date: "2026-04-22T14:32:27+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T17:05:01.988164+00:00"
model: auto
duration_s: 107.8
clone_size_kb: 16411
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

OpenCrust is a Rust-based runtime for running persistent AI assistants across multiple interfaces (web chat, terminal chat, APIs, and messaging channels) with tool use, memory, and optional multi-agent delegation. A user typically runs `opencrust start` to launch the gateway, then interacts via `opencrust chat`, browser UI, or channel adapters; each message is routed through an LLM tool loop with guardrails and persistence. The system combines operational automation features (scheduling, cross-channel messaging, file/shell/web tools) with knowledge features (document ingestion + retrieval, long-term memory). In practice, users get an always-on assistant that can execute workflows, retrieve docs, call external services (including MCP tools), and hand off subtasks to specialized named agents.

## 2. Agent Framework & Architecture

This repo uses a **custom Rust agent framework**, not LangGraph/LangChain/AutoGen/CrewAI. The core crate defines its own provider abstraction (`LlmProvider`), runtime (`AgentRuntime`), and tool trait (`Tool`) in `crates/opencrust-agents/src/lib.rs:1-33`, `crates/opencrust-agents/src/runtime.rs:58-106`, and `crates/opencrust-agents/src/tools/mod.rs:52-68`. Dependencies in `crates/opencrust-agents/Cargo.toml:8-35` show standard async/networking libraries plus optional `rmcp` for MCP, with no external agent-orchestration framework imports.

Architecture is centered on one runtime that can host multiple named agent profiles from config (`agents: HashMap<String, NamedAgentConfig>`), each with provider/model/system-prompt/tool/dna/skills overrides (`crates/opencrust-config/src/model.rs:38-42`, `240-260`). Routing to a profile happens at the gateway layer (`crates/opencrust-gateway/src/agent_router.rs:3-34`, `crates/opencrust-gateway/src/api.rs:153-191`, `crates/opencrust-gateway/src/ws.rs:438-492`), then execution stays in `AgentRuntime`.

The “intelligence” lives in: (a) LLM prompts assembled from base prompt + tools + DNA + skill blocks + RAG/memory context, and (b) iterative tool-calling loop logic in runtime (`crates/opencrust-agents/src/runtime.rs:1770-1894`). Multi-agent behavior is implemented via a first-class `handoff` tool that recursively calls the runtime with another named agent’s config (`crates/opencrust-agents/src/tools/handoff_tool.rs:12-22`, `130-176`).

## 3. Orchestration Pattern

Closest pattern: **hierarchical (manager-worker), with tool-loop execution inside each worker**.

The manager/worker behavior is explicit in `handoff`: one agent delegates a task to another `agent_id`, creates an isolated child session, applies that agent’s overrides, and invokes `process_message_with_agent_config_at_depth` (`crates/opencrust-agents/src/tools/handoff_tool.rs:130-176`). Depth is capped to prevent delegation cycles (`MAX_HANDOFF_DEPTH = 3`, `handoff_tool.rs:9-10`, `98-104`).

Within each agent run, control flow is a bounded iterative tool loop: LLM call -> inspect `ToolUse` blocks -> execute tools -> append tool results -> call LLM again, up to `MAX_TOOL_ITERATIONS` (`crates/opencrust-agents/src/runtime.rs:25-26`, `1798-1889`).

```1783:1889:crates/opencrust-agents/src/runtime.rs
let tool_defs = self.tool_definitions();
...
for _iteration in 0..MAX_TOOL_ITERATIONS {
    let request = LlmRequest { ... tools: tool_defs.clone(), };
    let response = provider.complete(&request).await?;
    let has_tool_use = response.content.iter().any(|block| matches!(block, ContentBlock::ToolUse { .. }));
    if !has_tool_use { ... return Ok(final_text); }
    messages.push(ChatMessage { role: ChatRole::Assistant, content: MessagePart::Parts(response.content.clone()) });
    let mut tool_results = Vec::new();
    for block in &response.content {
        if let ContentBlock::ToolUse { id, name, input } = block {
            let output = self.run_tool(..., name, input).await;
            tool_results.push(ContentBlock::ToolResult { tool_use_id: id.clone(), content: output.content });
        }
    }
    messages.push(ChatMessage { role: ChatRole::User, content: MessagePart::Parts(tool_results) });
}
```

```130:176:crates/opencrust-agents/src/tools/handoff_tool.rs
let handoff_session = format!("{}-handoff-{agent_id}", context.session_id);
let child_depth = context.heartbeat_depth + 1;
...
let result = runtime
    .process_message_with_agent_config_at_depth(
        &handoff_session, &message, &[], None, context.user_id.as_deref(),
        ac.provider.as_deref(), ac.model.as_deref(), ac.system_prompt.as_deref(),
        ac.max_tokens, ac.max_context_tokens, child_depth,
    )
    .await;
```

## 4. Tools & External Integrations

- **LLM providers (Anthropic/OpenAI/Ollama + OpenAI-compatible vendors)** wired in runtime bootstrap via `register_provider` (`crates/opencrust-gateway/src/bootstrap.rs:64-409`).
- **Shell/terminal execution** via `bash` tool (PowerShell on Windows, Bash on Unix) (`crates/opencrust-agents/src/tools/bash_tool.rs:11-13`, `62-71`).
- **Filesystem editing/search tools**: `file_read`, `file_write`, `file_patch`, `search_files` registered in bootstrap (`crates/opencrust-gateway/src/bootstrap.rs:413-418`).
- **Web retrieval/search**: `web_fetch` plus Brave or Google search tools (`crates/opencrust-gateway/src/bootstrap.rs:418`, `430-475`; implementations in `web_fetch_tool.rs:10-13`, `web_search_tool.rs:12-16`).
- **RAG/document store**: `doc_search`, `list_documents`, and ingestion-backed SQLite document store with optional embeddings (`crates/opencrust-gateway/src/bootstrap.rs:540-580`; `doc_search_tool.rs:35-44`, `120-127`).
- **Memory/trajectory persistence**: memory and trajectory stores in SQLite (`crates/opencrust-agents/src/runtime.rs:61-63`, `92-99`; bootstrap setup `478-538`, `612-624`).
- **MCP integrations** (stdio and HTTP): connection manager discovers server tools, bridges to internal tool trait, plus resource tool (`crates/opencrust-gateway/src/bootstrap.rs:706-800`; `crates/opencrust-agents/src/mcp/manager.rs:91-123`, `170-189`; `tool_bridge.rs:12-25`, `49-63`).
- **Cross-channel messaging tool**: `send_message` tool wired to channel dispatch queue (`crates/opencrust-gateway/src/bootstrap.rs:584-587`; `server.rs:384-433`).
- **Scheduler tools**: `schedule_heartbeat`, `cancel_heartbeat`, `list_heartbeats` backed by session DB (`crates/opencrust-gateway/src/server.rs:73-81`, `635-747`).

## 5. Notable Code Walkthrough

- `crates/opencrust-agents/src/runtime.rs:58-106,1770-1894` - Core runtime state + main LLM/tool loop; this is where prompts are assembled and tool-calling iterations are enforced.
- `crates/opencrust-agents/src/tools/handoff_tool.rs:9-10,130-176` - Multi-agent delegation primitive; creates isolated sub-session, applies target-agent config, and recursively executes with depth guard.
- `crates/opencrust-gateway/src/server.rs:38-57,91-94` - Runtime assembly point; attaches MCP tools and handoff tool, then wires handoff after `Arc` creation.
- `crates/opencrust-gateway/src/bootstrap.rs:412-418,430-475,540-580,706-800` - Central integration wiring for local tools, web search, RAG, memory, and MCP bridges.
- `crates/opencrust-gateway/src/ws.rs:438-492` - Per-request routing into named agent configs in live chat, including per-agent tool/DNA/skills overrides before runtime execution.

## 6. Use-Case Mapping

The assigned `Browser / Terminal Use` label is **partly accurate**: the project has explicit terminal interaction (`opencrust chat`) and browser/webchat endpoints, and the agent can execute shell commands and web fetch/search tools (`bash_tool.rs:11-13`, `web_fetch_tool.rs:10-13`). However, code-wise the broader and more central behavior is **workflow orchestration across tools/channels**: scheduled jobs, cross-channel send, persistent sessions/memory, and configurable role handoffs (`server.rs:73-81`, `635-747`; `handoff_tool.rs:130-176`). So this repository fits **Workflow Automation** better as primary, with browser/terminal use as one interface layer rather than the core research contribution.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Clear, explicit multi-agent delegation primitive with loop-depth safety (`handoff_tool.rs:9-10`, `98-104`).
- Strong runtime modularity: providers/tools are trait-based and registered dynamically (`runtime.rs:58-64`; `bootstrap.rs:412-418`).
- Practical orchestration stack combines tool loop, memory, RAG, scheduling, and channel adapters in one runtime.
- MCP integration is substantial (stdio+HTTP, tool bridging, handshake instructions, health/reconnect path) (`bootstrap.rs:706-800`; `manager.rs:91-123`).
- Operational guardrails (tool allowlists/budgets, token budgets, input checks) are applied around message execution (`ws.rs:324-356`; `api.rs:139-144`).

- **Limitations:**
- Orchestration is primarily prompt-driven + recursive calls, not declarative graph/state-machine planning; control logic can be hard to verify formally.
- Multi-agent collaboration seems mostly pairwise via `handoff` rather than richer shared-blackboard or consensus patterns.
- Tool loop has fixed max iterations (`MAX_TOOL_ITERATIONS=10`), which can truncate complex workflows without adaptive planning.
- Reliability depends heavily on per-agent prompts and config quality; no explicit learned router policy in core code.
- Significant runtime complexity is concentrated in very large files (notably `runtime.rs`, `bootstrap.rs`), which may hinder maintainability.

- **Research relevance:**
- Good evidence of **production-oriented MAS engineering** in Rust with explicit delegation and safety bounds.
- Illustrates how MCP servers can be operationalized as first-class tools in an agent runtime.
- Useful case study for integrating **memory + RAG + tool use + scheduling** in one continuously running assistant.
- Demonstrates config-driven role specialization (tools/prompt/DNA/skills) as a practical alternative to heavyweight agent frameworks.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
