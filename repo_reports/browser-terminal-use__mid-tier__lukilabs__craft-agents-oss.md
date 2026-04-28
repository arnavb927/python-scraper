---
repo_name: lukilabs/craft-agents-oss
url: "https://github.com/lukilabs/craft-agents-oss"
stars: 4475
forks: 664
contributors_count: 7
last_commit_date: "2026-04-22T11:27:22+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T12:15:40.361248+00:00"
model: auto
duration_s: 136.1
clone_size_kb: 34606
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`craft-agents-oss` is a TypeScript monorepo for running a persistent “coding/automation agent” with desktop and headless server modes. A user runs either the Electron app or the headless server entrypoint (`packages/server/src/index.ts`) and gets long-lived sessions that can use LLMs, tools, MCP sources, browser automation, and session-level workflow actions. Under the hood, it supports two backend agent runtimes (Anthropic SDK path and Pi SDK path) behind one common session manager. The system is more than a chat UI: it manages multi-session workspaces, source integrations, automations, and cross-session task delegation. In practice, users get an operational agent workspace where sessions can create/spawn other sessions, call tools, and coordinate ongoing work.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex as its primary runtime. It is a **custom orchestration layer** over provider SDKs, mainly:
- `@anthropic-ai/claude-agent-sdk` (`packages/shared/src/agent/claude-agent.ts:1`)
- `@mariozechner/pi-coding-agent` and `@mariozechner/pi-ai` (`packages/pi-agent-server/src/index.ts:24-56`)

Architecture is split into:
1. **Session/orchestration layer** (`SessionManager`) that owns workspaces, sessions, lifecycle, permissions, source activation, automations, and cross-session control (`packages/server-core/src/sessions/SessionManager.ts:2551-2810`, `3400-3456`).
2. **Backend abstraction layer** (`createBackendFromResolvedContext`) that chooses Anthropic vs Pi backend from connection context (`packages/shared/src/agent/backend/factory.ts:158-189`, `353-380`).
3. **Backend runtime implementations** (`PiAgent`, `ClaudeAgent`) that run model conversations and tool routing. Pi runs as an out-of-process JSONL subprocess (`packages/shared/src/agent/pi-agent.ts:324-515`; `packages/pi-agent-server/src/index.ts:1-15`).

“Intelligence” is concentrated in system prompts + tool-rich agent loops, not in explicit graph state machines. Prompt construction and runtime behavior are shaped by source context, permission/pre-tool pipelines, and session tools (`packages/shared/src/agent/pi-agent.ts:1841-1914`; `packages/session-tools-core/src/tool-defs.ts:530-561`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with event-driven extensions**.

- **Manager-worker core**: `SessionManager` is the orchestrator; each session owns one backend agent worker instance. It lazily creates agents, configures tools/sources, and handles callbacks (`packages/server-core/src/sessions/SessionManager.ts:2551-2810`).
- **Event-driven runtime**: agent/subprocess emits tool and lifecycle events; manager reacts (permission prompts, source activation, plan submission pause, auth handoff) (`packages/shared/src/agent/pi-agent.ts:813-1071`, `1073-1276`).

Representative control-flow excerpts:

```2551:2564:packages/server-core/src/sessions/SessionManager.ts
private async getOrCreateAgent(managed: ManagedSession): Promise<AgentInstance> {
  if (!managed.agent) {
    const end = perf.start('agent.create', { sessionId: managed.id })
    ...
```

```3400:3446:packages/server-core/src/sessions/SessionManager.ts
managed.agent.onSpawnSession = async (request) => {
  const session = await this.createSession(managed.workspace.id, { ... })
  ...
  this.sendMessage(session.id, request.prompt, fileAttachments).catch(err => {
```

This demonstrates parent session/manager delegating work into new autonomous child sessions (runtime multi-agent behavior).

## 4. Tools & External Integrations

- **MCP protocol + MCP servers**: session MCP server implemented with `@modelcontextprotocol/sdk` (`packages/session-mcp-server/src/index.ts:24-33`, `511-569`), plus dynamic source MCP tool pooling in session manager/backends (`packages/server-core/src/sessions/SessionManager.ts:2621-2631`; `packages/shared/src/agent/pi-agent.ts:1344-1347`).
- **LLM provider SDKs**: Anthropic SDK and Pi SDK abstraction (`packages/shared/src/agent/backend/factory.ts:26-28`, `132-145`).
- **Web search**: provider-resolved `web_search` tool with fallback (`packages/pi-agent-server/src/tools/search/create-search-tool.ts:56-114`; provider resolution in `packages/pi-agent-server/src/index.ts:520-529`).
- **Web fetch**: `web_fetch` tool with SSRF checks, content-type handling, PDF/image extraction (`packages/pi-agent-server/src/tools/web-fetch.ts:319-419`, `42-94`).
- **Browser automation**: unified `browser_tool` command runtime (navigate/click/snapshot/evaluate/screenshot/etc.) (`packages/shared/src/agent/browser-tool-runtime.ts:40-113`, `622-680` and onward).
- **Terminal/file coding tools** (Pi path): built-in tool defs include `read`, `bash`, `edit`, `write`, `grep`, `find`, `ls` (`packages/pi-agent-server/src/index.ts:29-36`, `543-551`).
- **Cross-session workflow tools**: `spawn_session`, `send_agent_message`, `list_sessions`, status/labels tools in canonical registry (`packages/session-tools-core/src/tool-defs.ts:164-214`, `530-560`).
- **Docs MCP upstream proxy**: session MCP server proxies docs tools from `https://agents.craft.do/docs/mcp` (`packages/session-mcp-server/src/index.ts:275-337`, `524-556`).

## 5. Notable Code Walkthrough

- `packages/server-core/src/sessions/SessionManager.ts:2551-2810,3400-3456`  
  Central orchestrator: resolves backend context, creates per-session agents, wires callbacks, and enables child-session spawning from tool calls.

- `packages/shared/src/agent/backend/factory.ts:158-189,353-380`  
  Provider-agnostic backend factory that maps LLM connection config into concrete runtime (`ClaudeAgent` vs `PiAgent`) and capabilities.

- `packages/shared/src/agent/pi-agent.ts:324-515,1073-1354,1767-1937`  
  Pi backend transport/client: spawns subprocess, registers proxy tools, enforces pre-tool checks, routes session/MCP tools, and streams events per turn.

- `packages/pi-agent-server/src/index.ts:501-658,792-852,1090-1175`  
  Out-of-process Pi runtime where session is actually created, built-in+web+proxy tools are wrapped, and tool events are bridged back to main process.

- `packages/session-tools-core/src/tool-defs.ts:530-561`  
  Canonical session tool registry defining backend vs registry execution modes, including `spawn_session`, `call_llm`, `browser_tool`, and inter-session messaging tools.

## 6. Use-Case Mapping

Although it includes strong **Browser / Terminal Use** capabilities (browser command runtime plus coding tools like bash/read/edit/write), the repository’s core runtime is broader: it emphasizes **session orchestration and delegated multi-session workflows** with automations, status/labels, source activation, and inter-session messaging.

Concretely, browser/terminal functionality is realized by:
- terminal/coding tools in Pi runtime (`packages/pi-agent-server/src/index.ts:543-551`),
- browser control through `browser_tool` (`packages/shared/src/agent/browser-tool-runtime.ts:622-680`),
- permission-gated tool execution pipeline (`packages/shared/src/agent/pi-agent.ts:1073-1276`).

Given the built-in delegated session workflows (`spawn_session`, `send_agent_message`) and automation-triggered session creation (`packages/server-core/src/sessions/SessionManager.ts:1343-1358`), the better top-level category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Unified backend abstraction across heterogeneous SDKs with shared orchestration (`packages/shared/src/agent/backend/factory.ts:158-189`).
  - Real runtime multi-agent delegation via session spawning and cross-session messaging (`SessionManager.ts:3400-3456`; `tool-defs.ts:474-479`).
  - Strong tool governance: pre-tool checks, permission modes, and source activation gating (`pi-agent.ts:1117-1215`).
  - Rich integration surface (MCP, browser, web search/fetch, automation hooks) in one coherent stack.
  - Practical resilience patterns (subprocess isolation, token refresh, fallback models, compaction handling).

- **Limitations:**
  - Architecture is complex and distributed across manager/backend/subprocess layers, increasing maintenance burden.
  - No explicit declarative planning graph/state-machine framework; behavior is callback/event heavy and harder to formally verify.
  - Heavy dependence on custom protocol glue (JSONL IPC, callback channels), which can be fragile across runtime boundaries.
  - Some backend behavior differs by provider path (Anthropic vs Pi), requiring parity guardrails and extra tests.
  - Large monorepo + many conditional paths can make reproducible benchmarking difficult.

- **Research relevance:**
  - Evidence of production-style **manager + delegated workers** MAS pattern in developer-agent systems.
  - Useful case study in **tool-governed agent autonomy** (permission pipelines + dynamic tool activation).
  - Demonstrates **cross-session coordination** primitives (spawn/message/list/status) as an alternative to in-turn multi-agent debate.
  - Shows practical integration of MCP ecosystems into long-lived autonomous sessions.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
