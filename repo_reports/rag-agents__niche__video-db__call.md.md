---
repo_name: video-db/call.md
url: "https://github.com/video-db/call.md"
stars: 287
forks: 30
contributors_count: 4
last_commit_date: "2026-04-14T16:46:53+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:35:56.461356+00:00"
model: auto
duration_s: 78.9
clone_size_kb: 7698
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`call.md` is an Electron desktop app that records meetings, streams dual-channel transcription (“me” vs “them”), and runs live AI assistance during calls. A user launches the app, authenticates with a VideoDB API key, starts a meeting recording, and then receives real-time coaching prompts plus optional MCP-powered lookups. After the call, the system generates structured summaries/action items and can trigger outbound workflow webhooks (e.g., n8n/Zapier-style automation). Core runtime behavior is local-first (SQLite + desktop process orchestration) with cloud APIs used for LLM/transcription and external integrations.

## 2. Agent Framework & Architecture

This repo does **not** use CrewAI, LangGraph, AutoGen, or LangChain in code imports. The “agentic” logic is a **custom architecture** built around:
- OpenAI SDK client against a VideoDB-compatible base URL (`src/main/services/llm.service.ts:8-14`, `:205-210`, `:330-337`)
- MCP SDK-backed tool servers (`@modelcontextprotocol/sdk` in `package.json:33`)
- Event/timer loops in Electron main process services.

High-level architecture has multiple LLM-driven services with different roles:
1. **Live Assist loop** generates “say_this / ask_this” coaching from rolling transcript windows (`src/main/services/live-assist.service.ts:17-25`, `:231-264`).
2. **MCP Inference loop** decides when to call connected MCP tools and renders short “findings” (`src/main/services/mcp-inference.service.ts:19-24`, `:303-339`).
3. **Post-call Summary Generator** runs three specialized summarization prompts in parallel (`src/main/services/copilot/summary-generator.service.ts:45-63`, `:156-161`).

“Intelligence” lives mostly in hardcoded system prompts and tool-calling loops rather than a formal graph planner. There is also an `MCPAgentService` class with persistent chat+tool loop (`src/main/services/mcp/mcp-agent.service.ts:264-273`, `:338-390`), but it appears largely unused in runtime flow compared to `mcp-inference.service`.

## 3. Orchestration Pattern

Closest fit: **event-driven + periodic sequential loops** (not hierarchical manager-worker, not LangGraph state machine).

Control flow is driven by IPC events and timed inference cycles:

```31:58:src/main/ipc/live-assist.ts
export function setupLiveAssistHandlers(): void {
  ipcMain.handle('live-assist:start', async (_event, context?: MeetingContext) => {
    const liveAssistService = getLiveAssistService();
    ...
    liveAssistService.start(context);

    const mcpInferenceService = getMCPInferenceService();
    ...
    mcpInferenceService.start();
```

Each loop then runs a bounded tool-calling while-loop:

```303:339:src/main/services/mcp-inference.service.ts
while (toolsCalled < MAX_TOOL_CALLS_PER_RUN) {
  const response = await llm.chatCompletionWithTools(messages, tools);
  if (response.tool_calls && response.tool_calls.length > 0) {
    ...
    for (const toolCall of response.tool_calls) {
      toolsCalled++;
      const result = await this.executeToolCall(toolCall);
      messages.push({ role: 'tool', tool_call_id: toolCall.id, ... });
    }
    continue;
  }
```

So orchestration is mostly: transcript events -> buffer -> every 20s LLM pass -> optional tool calls -> UI events.

## 4. Tools & External Integrations

- **OpenAI-compatible LLM endpoint (via VideoDB base URL)**: centralized in `LLMService` (`src/main/services/llm.service.ts:93-109`, `:310-337`).
- **MCP servers/tools (stdio + HTTP + OAuth)**: connection lifecycle and tool execution in `ConnectionOrchestratorService` (`src/main/services/mcp/connection-orchestrator.service.ts:80-114`, `:230-252`, `:335-364`, `:477-541`).
- **MCP tool catalog/search**: aggregated across connected servers in `ToolAggregatorService` (`src/main/services/mcp/tool-aggregator.service.ts:34-41`, `:101-110`).
- **VideoDB SDK (recording/transcription/video operations)**: `videodb` integration in `src/main/services/videodb.service.ts:1-4`, `:142-179`, `:194-233`.
- **Workflow automation webhooks (n8n/Zapier/CRM endpoints)**: outbound POST calls in `src/main/services/workflow-webhook.service.ts:41-49`, `:113-123`.
- **Google Calendar API**: authenticated calendar fetch and event parsing in `src/main/services/google-calendar.service.ts:13-14`, `:33-43`, `:136-159`.
- **Local SQLite persistence (Drizzle)**: used broadly for settings/transcripts/recordings/tool-call logs (e.g., DB calls in `src/main/ipc/mcp.ts:16-17`, `:237-256`; `src/main/services/copilot/sales-copilot.service.ts:13-18`).

No dedicated vector DB (e.g., Chroma/Pinecone/pgvector) is evident in core runtime code.

## 5. Notable Code Walkthrough

- `src/main/services/llm.service.ts:87-125, 310-405` - Shared LLM wrapper used across features; supports normal chat and OpenAI function-calling/tool loops, making it the core “agent runtime primitive.”
- `src/main/services/mcp-inference.service.ts:22-61, 250-379` - Real-time meeting inference loop; every 20s it evaluates transcript context, invokes MCP tools when needed, and emits renderer-facing “MCP Findings.”
- `src/main/services/live-assist.service.ts:19-74, 231-307` - Separate live coach agent that generates conversational nudges (“say this / ask this”) from short rolling windows plus meeting/screen context.
- `src/main/ipc/live-assist.ts:31-85` - Runtime wiring layer that starts/stops both live loops together and forwards transcript chunks to both services.
- `src/main/services/copilot/summary-generator.service.ts:45-98, 139-169` - Post-meeting batch intelligence: runs three prompt-specialized summary tasks concurrently and parses structured outputs.

## 6. Use-Case Mapping

The assigned label **RAG + Agents** is only partially accurate. The repository clearly implements **agent-like LLM loops with tool calling** (especially via MCP), but it does **not** implement a classical document-retrieval RAG pipeline (no embedded vector-index retrieval stack in core app code). Instead, tool retrieval is delegated to MCP tools and external systems, and the dominant business workflow is meeting capture -> live assist -> post-call artifacts -> webhook automation.

Best fit after code inspection: **Workflow Automation** (with embedded agentic assistance), not pure RAG-centric architecture.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear production-oriented event architecture tying transcription, live inference, and UI updates (`src/main/ipc/live-assist.ts:31-85`).
  - Strong tool integration story through MCP (multi-server registry, transport options, OAuth, tool discovery) (`src/main/services/mcp/connection-orchestrator.service.ts:80-114`, `:430-450`).
  - Practical bounded agent loops with guardrails (`MAX_TOOL_CALLS_PER_RUN`, prompt constraints) (`src/main/services/mcp-inference.service.ts:20`, `:303-344`).
  - Specialized prompt decomposition for post-call outputs improves task focus (`src/main/services/copilot/summary-generator.service.ts:45-129`).
  - Local-first persistence and desktop packaging make it deployable beyond demos.

- **Limitations:**
  - “Multi-agent” coordination is weak; loops are parallel but mostly independent, without shared planner/router policy between agents.
  - Some agent-related code seems underutilized (`MCPAgentService` and `IntentDetectorService` are present but not clearly wired into live runtime path).
  - No explicit retrieval/index layer in repo for robust long-context grounding; depends on external MCP/tool quality.
  - Prompt logic and heuristics are hardcoded in services, limiting dynamic policy adaptation.
  - Limited visible evaluation/test harness for agent quality/regression in this code path.

- **Research relevance:**
  - Good example of **event-driven agentic UX** in a desktop app (continuous transcript-to-action loop).
  - Useful case of **LLM + MCP tool ecosystems** integrated with real-time human workflows.
  - Demonstrates pragmatic bounded tool-calling loops rather than benchmark-style multi-agent deliberation.
  - Shows how agent outputs can be operationalized into downstream automations (webhooks) in end-user products.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
