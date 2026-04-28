---
repo_name: 7836246/cursor2api
url: "https://github.com/7836246/cursor2api"
stars: 1773
forks: 503
contributors_count: 7
last_commit_date: "2026-04-03T01:13:57+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T14:19:13.904043+00:00"
model: auto
duration_s: 69.1
clone_size_kb: 1599
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`cursor2api` is a TypeScript proxy server that sits between clients (Claude Code, Cursor IDE, OpenAI-compatible clients) and Cursor’s hidden `https://cursor.com/api/chat` endpoint, translating protocols in both directions (`src/index.ts:108-118`, `src/cursor-client.ts:16-17`). Users run the server (`npm run dev` / `npm start`) and point their client to local `/v1/messages`, `/v1/chat/completions`, or `/v1/responses` endpoints, receiving Anthropic/OpenAI-compatible responses instead of Cursor-native SSE payloads (`src/index.ts:108-151`). The core value is compatibility and robustness: tool-call formatting, refusal/retry handling, truncation continuation, and optional image/OCR preprocessing are all handled by middleware logic (`src/handler.ts`, `src/openai-handler.ts`, `src/converter.ts`, `src/vision.ts`). In practice, this is an agent-runtime adapter, not an agent framework itself.

## 2. Agent Framework & Architecture

No mainstream agent framework (LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex) is actually used in runtime code. Imports are custom Express handlers plus local modules (`src/index.ts`, `src/handler.ts`, `src/openai-handler.ts`, `src/converter.ts`), and package dependencies also lack those frameworks (`package.json:26-36`).

Architecture is a custom protocol-conversion pipeline:
1) HTTP API ingress (`/v1/messages`, `/v1/chat/completions`, `/v1/responses`) in `src/index.ts`;  
2) Request normalization/conversion and prompt/tool-instruction injection in `src/converter.ts`;  
3) Upstream call to Cursor chat backend in `src/cursor-client.ts`;  
4) Response postprocessing (tool-call parsing, retries, truncation continuation, format conversion back to Anthropic/OpenAI) in `src/handler.ts` and `src/openai-handler.ts`.

“Intelligence” mostly lives in prompt engineering and parsing heuristics, not in multiple cooperating agent objects: `buildToolInstructions(...)` and few-shot injection drive tool behavior (`src/converter.ts:90-180`, `src/converter.ts:421-547`), while `parseToolCalls(...)` and retry/continuation logic recover structured tool actions from generated text (`src/converter.ts:1252-1346`, `src/handler.ts:1457-1516`).

## 3. Orchestration Pattern

Closest pattern: **other (single-agent tool-calling loop with middleware orchestration)**, implemented as a sequential request/response pipeline rather than multi-agent coordination.

Control flow is linear and centralized in handlers:

```489:497:src/openai-handler.ts
// Step 2: Anthropic → Cursor 格式（复用现有管道）
const cursorReq = await convertToCursorRequest(anthropicReq);
log.recordCursorRequest(cursorReq);

if (body.stream) {
    await handleOpenAIStream(res, cursorReq, body, anthropicReq, log);
} else {
    await handleOpenAINonStream(res, cursorReq, body, anthropicReq, log);
}
```

And tool orchestration is text-block based (parse generated `json action` blocks, then emit protocol-native tool calls), not agent-to-agent routing:

```1658:1666:src/handler.ts
if (toolCalls.length > 0) {
    stopReason = 'tool_use';

    // Check if the residual text is a known refusal, if so, drop it completely!
    if (isRefusal(cleanText)) {
        log.info('Handler', 'sanitize', `抑制工具调用中的拒绝文本`, { preview: cleanText.substring(0, 200) });
        cleanText = '';
    }
```

## 4. Tools & External Integrations

- **Cursor backend API** (`https://cursor.com/api/chat`) via fetch/SSE in `src/cursor-client.ts:16-17,57-67,129-135`.
- **Anthropic-compatible API surface** for clients (`/v1/messages`) wired in `src/index.ts:108-110`, processed in `src/handler.ts`.
- **OpenAI Chat Completions + Responses compatibility** wired in `src/index.ts:113-118`, processed in `src/openai-handler.ts`.
- **Tool-calling bridge (JSON action format)** injected and parsed in `src/converter.ts:90-180,1252-1346`; this is how external agent clients’ tools are represented.
- **Vision/OCR pipeline**: local OCR via `tesseract.js` and optional external vision API call in `src/vision.ts:4,49-53,114-162`; invoked from `src/converter.ts:1710-1713`.
- **Proxy support** using `undici` `ProxyAgent` for upstream and vision APIs in `src/proxy-agent.ts:12,22-43,49-63`.
- **SQLite logging storage** (`better-sqlite3`) initialized from `src/index.ts:157-160` (implementation in `src/logger-db.ts`).
- **Stealth proxy integration** (optional browser-mediated upstream route) selected in `src/cursor-client.ts:90-99`, configured in `src/config.ts:58-60,217-218`.
- **No vector DB/RAG index stack** (no Chroma/Pinecone/pgvector retrieval code found in `src/`).

## 5. Notable Code Walkthrough

- `src/index.ts:108-151` — Defines the public API contract (`/v1/messages`, `/v1/chat/completions`, `/v1/responses`) and exposes this project as a drop-in compatibility proxy.
- `src/converter.ts:210-854` — Core transformation engine: converts Anthropic-format requests into Cursor chat payloads, injects tool instructions/few-shot behavior, applies history budgeting/compression, and preprocesses images.
- `src/handler.ts:344-419` — Main Anthropic request handler orchestrating conversion, identity/refusal guards, stream vs non-stream execution, and response shaping.
- `src/openai-handler.ts:98-244` — Converts OpenAI requests/messages/tools into internal Anthropic representation, enabling protocol unification through the same backend pipeline.
- `src/cursor-client.ts:57-167` — Low-level upstream transport: sends requests to Cursor, streams SSE chunks, retries failures, and handles timeout/degenerate-loop conditions.

## 6. Use-Case Mapping

The upstream label **“RAG + Agents”** does not match the actual implementation. The repo does not implement a retrieval pipeline (no embedding/index/retriever/vector-store flow), and it does not instantiate multiple coordinated LLM agents at runtime. Instead, it provides **workflow middleware** for agentic clients: protocol translation, tool-call formatting/parsing, retry/continuation control, and transport hardening so external agent loops (e.g., Claude Code) can run through Cursor infrastructure.  
A better category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Strong protocol interoperability across Anthropic, OpenAI Chat Completions, and OpenAI Responses (`src/index.ts`, `src/openai-handler.ts`).
- Robust tool-call recovery from noisy/truncated model text via tolerant parsing and continuation (`src/converter.ts:1058-1241,1252-1346`; `src/handler.ts:1457-1545`).
- Practical production hardening: retries, keepalive, idle timeout, degenerate-loop detection (`src/cursor-client.ts:109-124,151-167,184-252`).
- Flexible tool schema injection modes (`compact/full/names_only`, passthrough/disabled) for context budget tradeoffs (`src/converter.ts:97-143,273-307`).
- Multimodal fallback path (local OCR or external vision API) integrated into request preprocessing (`src/vision.ts`, `src/converter.ts:1434-1732`).

- **Limitations:**
- No true multi-agent runtime; orchestration is single-model + middleware, so MAS research claims would be overstated.
- Heavy reliance on prompt injection/few-shot shaping of tool behavior may be brittle across upstream model changes (`src/converter.ts:421-547`).
- Tool protocol depends on model emitting textual code blocks (` ```json action `), not native function-call channels, increasing parse fragility.
- Extensive refusal/identity rewrite heuristics are regex-heavy and may cause over-filtering or unintended text mutation (`src/handler.ts:203-305`).
- Upstream dependency on undocumented Cursor API behavior is a maintenance risk (`src/cursor-client.ts:16-17`).

- **Research relevance:**
- Useful evidence for **middleware-based agent enablement**: how protocol adapters can make one backend usable by heterogeneous agent clients.
- Demonstrates **heuristic recovery techniques** for tool-call extraction from imperfect LLM outputs.
- Illustrates engineering patterns for **long-running agent loop reliability** (continuation, retries, stream keepalive, timeout handling).
- Relevant for studies on **practical agent infrastructure**, not for multi-agent coordination algorithms.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
