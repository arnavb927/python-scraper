---
repo_name: THU-MAIC/OpenMAIC
url: "https://github.com/THU-MAIC/OpenMAIC"
stars: 16274
forks: 3028
contributors_count: 21
last_commit_date: "2026-04-20T05:41:17+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 9
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T09:14:50.381876+00:00"
model: auto
duration_s: 87.4
clone_size_kb: 174466
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`OpenMAIC` is a Next.js application that generates and runs AI-powered interactive classrooms where multiple role-based agents (teacher/assistant/students) speak, act on slides/whiteboard, and continue turn-by-turn discussion. A user typically runs the web app, configures model/provider and agent roster, then starts chat or auto-generation endpoints to produce scenes, actions, and dialogue streams. The runtime sends stateless requests to `/api/chat`, where a director selects which agent speaks and each agent emits structured text+action events over SSE. Beyond classroom chat, the repo also includes a PBL (project-based learning) generation subsystem that uses tool-calling to construct project roles/issues and a runtime PBL chat endpoint. The practical output is a playable classroom/presentation experience with orchestrated multi-agent teaching behaviors rather than a single chatbot response.

## 2. Agent Framework & Architecture

The project **does use LangGraph/LangChain**, confirmed by imports from `@langchain/langgraph` and `@langchain/core/messages` in `lib/orchestration/director-graph.ts:20-23`. It also uses the Vercel AI SDK (`ai`) as the model-call layer (`lib/ai/llm.ts:7-9`) and for tool-calling loops in PBL generation (`lib/pbl/generate-pbl.ts:11-13`). So architecture is hybrid: **LangGraph for classroom multi-agent turn orchestration + AI SDK for model abstraction and PBL tool loops**.

In classroom chat, agent “intelligence” is split across:
- director prompt/routing logic (`buildDirectorPrompt` + parse decision) in `lib/orchestration/director-graph.ts:167-191`;
- role/system prompt construction in `lib/orchestration/prompt-builder.ts:123-165`;
- structured output parser enforcing interleaved `text` and `action` JSON objects in `lib/orchestration/stateless-generate.ts:117-136`.

There are multiple agent configs in registry/request state; the graph runs one selected agent per turn, streams events (`agent_start`, `text_delta`, `action`), then loops back to director (`lib/orchestration/director-graph.ts:472-494`). In PBL generation, a separate “designer” loop uses tool calls over MCP-like state managers (`AgentMCP`, `IssueboardMCP`) to synthesize a multi-agent project configuration (`lib/pbl/generate-pbl.ts:59-72`).

## 3. Orchestration Pattern

Closest fit: **graph-based hierarchical manager-worker**.

- It is graph-based because control flow is an explicit LangGraph state machine:  
```477:492:lib/orchestration/director-graph.ts
 * Topology:
 *   START → director ──(end)──→ END
 *              │
 *              └─(next)→ agent_generate ──→ director (loop)
...
.addEdge(START, 'director')
.addConditionalEdges('director', directorCondition, {
  agent_generate: 'agent_generate',
  [END]: END,
})
.addEdge('agent_generate', 'director');
```

- It is hierarchical because a **director node** decides which worker agent speaks next, including USER/END decisions:  
```153:204:lib/orchestration/director-graph.ts
// ── Multi agent: LLM-based decision ──
...
const decision = parseDirectorDecision(content);

if (decision.shouldEnd || !decision.nextAgentId) {
  return { shouldEnd: true };
}
if (decision.nextAgentId === 'USER') {
  write({ type: 'cue_user', ... });
  return { shouldEnd: true };
}
```

Client-side looping over one-turn server calls further reinforces this manager-worker cycle (`lib/chat/agent-loop.ts:102-110`, `:195-203`).

## 4. Tools & External Integrations

- **LLM providers via Vercel AI SDK**: OpenAI, Anthropic, Google, plus many OpenAI-compatible providers (DeepSeek/Qwen/Kimi/GLM/etc.) are wired in provider registry and model factory (`lib/ai/providers.ts:56-57`, `:1172-1292`).
- **LangGraph runtime integration**: orchestration graph compiles and streams with `streamMode: 'custom'` (`lib/orchestration/stateless-generate.ts:331-338`).
- **Structured in-app action tools (not external APIs)**: agents output actions like `spotlight`, `wb_draw_*`, `play_video`, filtered by scene type (`lib/orchestration/tool-schemas.ts:16-21`, `:29-61`).
- **Web search API (Tavily)**: `/api/web-search` rewrites query (optionally via LLM) and calls Tavily REST through `proxyFetch` (`app/api/web-search/route.ts:77-87`, `lib/web-search/tavily.ts:28-40`).
- **Media generation services**: server-side image/video generation and TTS synthesis through provider abstractions (`lib/server/classroom-media-generation.ts:12-17`, `:105-108`, `:151-154`, `:256-266`).
- **PBL tool-calling “MCP-style” managers**: internal classes (`AgentMCP`, `IssueboardMCP`, etc.) are invoked as AI SDK tools during generation (`lib/pbl/generate-pbl.ts:70-79`, `:118-147`, `:178-229`).
- **No browser automation / terminal control by agents** in the runtime code paths inspected; no Playwright/tool-use loop exposed as agent tools.

## 5. Notable Code Walkthrough

- `lib/orchestration/director-graph.ts:47-75,100-226,482-494`  
  Defines LangGraph state, director decision logic, and graph edges. This is the core multi-agent orchestrator that picks next speaker and loops until cue/end.
- `lib/orchestration/stateless-generate.ts:317-434`  
  Wraps graph execution into streaming SSE events and emits final `done` payload with director state, enabling stateless turn continuation.
- `lib/orchestration/prompt-builder.ts:123-165,175-198`  
  Builds role-aware system prompts (teacher/assistant/student), language constraints, peer context, and action guidelines; this is where much agent behavior policy is encoded.
- `app/api/chat/route.ts:44-90,125-143,182-189`  
  Main chat endpoint: validates request, resolves model/provider, calls orchestration generator, and streams SSE back to client.
- `lib/pbl/generate-pbl.ts:43-49,70-79,285-295,320-326`  
  Separate agentic generation loop using AI SDK tool-calling to construct PBL project structures and role/issue boards.

## 6. Use-Case Mapping

Although tagged as `Simulation`, the dominant runtime pattern is **automating a structured teaching workflow**: choose next speaker, generate pedagogical utterance + action sequence, update board/scene state, and continue until stop conditions. This is not primarily a physics/agent-based simulation engine; instead it orchestrates multi-role educational workflow execution with stateful turn management (`lib/chat/agent-loop.ts:99-110`, `lib/orchestration/director-graph.ts:88-99`). The interactive widget branch does include simulation-type content generation (`lib/generation/scene-generator.ts:987-997`), but that is one content subtype within a broader orchestration product. So a better primary category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Real multi-agent runtime with explicit director/worker loop and turn memory (`lib/orchestration/director-graph.ts`).
  - Strong stateless server design: full state travels in request/response, easing horizontal scaling (`app/api/chat/route.ts:7-13`, `lib/orchestration/director-graph.ts:505-539`).
  - Structured action+text protocol with robust partial JSON parsing/fallbacks (`lib/orchestration/stateless-generate.ts:117-136`, `:265-306`).
  - Rich role/policy prompting (teacher vs assistant vs student) with context-aware constraints (`lib/orchestration/prompt-builder.ts:18-43`, `:175-198`).
  - Broad provider abstraction and reasoning/thinking adaptation across vendors (`lib/ai/llm.ts:129-189`, `lib/ai/providers.ts:1031-1133`).

- **Limitations:**
  - Director decisions rely heavily on prompt parsing and free-form LLM output; no formal verifier beyond `parseDirectorDecision` fallback behavior (`lib/orchestration/director-graph.ts:190-210`).
  - Tool/action execution is mostly “soft constrained” via prompt + filtering, not capability-isolated function-calling in classroom loop (`lib/orchestration/tool-schemas.ts`, `director-graph` action filtering).
  - Some generation fallbacks are heuristic/default text, which may reduce pedagogical consistency (`lib/generation/scene-generator.ts:1521-1574`).
  - PBL generation loop uses a step cap (`stepCountIs(30)`), so complex projects may terminate incomplete (`lib/pbl/generate-pbl.ts:294`, `:311-315`).

- **Research relevance:**
  - Good reference for **LLM-directed multi-agent conversation orchestration** implemented as a state graph.
  - Useful evidence for **hybrid symbolic+LLM control** (hard turn limits/conditions + LLM routing decisions).
  - Demonstrates **stateless multi-turn MAS serving** via streaming events and client-managed continuation.
  - Shows practical integration of **agent action channels** (speech + UI actions) in educational HCI settings.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
