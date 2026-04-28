---
repo_name: ZeframLou/call-me
url: "https://github.com/ZeframLou/call-me"
stars: 2588
forks: 252
contributors_count: 3
last_commit_date: "2026-04-07T00:15:20+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Browser / Terminal Use]
generated_at: "2026-04-27T14:03:56.025919+00:00"
model: auto
duration_s: 65.7
clone_size_kb: 3053
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`call-me` is a Claude Code plugin plus local MCP server that lets Claude place a real phone call to the user, speak a message, and transcribe the user’s spoken reply back into text. A user installs the plugin, configures phone/OpenAI/ngrok credentials, and Claude can invoke tools like `initiate_call`, `continue_call`, `speak_to_user`, and `end_call` during normal task execution (`.claude-plugin/plugin.json:13-32`, `server/src/index.ts:75-131`). The server bridges MCP stdio to telephony webhooks/WebSockets, handling call setup, audio streaming, STT, and TTS (`server/src/phone-call.ts:87-217`, `server/src/phone-call.ts:438-547`). Practically, this solves “step away from keyboard but stay in the loop” by turning asynchronous agent updates/questions into live voice interactions.

## 2. Agent Framework & Architecture

The code does **not** use LangGraph, LangChain, CrewAI, AutoGen, or LlamaIndex. It uses a **custom MCP tool server architecture** via `@modelcontextprotocol/sdk` (`server/src/index.ts:10-13`, `server/package.json:12-17`).

Architecturally, there is one MCP server process exposing four tools to an upstream LLM agent (Claude Code). The intelligence/planning is outside this repo (in Claude); this repo implements execution plumbing: tool handlers map directly to `CallManager` methods (`server/src/index.ts:134-183`), and `CallManager` manages call state, provider interactions, and turn-taking (`server/src/phone-call.ts:70-77`, `server/src/phone-call.ts:438-717`).

Internally, the code is modular by provider abstraction rather than by multiple LLM roles. `createProviders()` wires phone (Twilio/Telnyx), TTS (OpenAI/Kokoro), and STT (OpenAI Realtime) behind interfaces (`server/src/providers/index.ts:72-124`, `server/src/providers/types.ts:11-146`), but these are service adapters, not independent agents.

## 3. Orchestration Pattern

Closest match: **event-driven single-agent tool backend** (not MAS).  
Control flow is request/handler dispatch from MCP tool calls, then asynchronous webhook/WebSocket events drive state transitions.

Example 1 (tool-dispatch orchestration):

```134:175:server/src/index.ts
mcpServer.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === 'initiate_call') {
    const { message } = request.params.arguments as { message: string };
    const result = await callManager.initiateCall(message);
    ...
  }
  if (request.params.name === 'continue_call') {
    const { call_id, message } = request.params.arguments as { call_id: string; message: string };
    const response = await callManager.continueCall(call_id, message);
```

Example 2 (event/webhook-driven progression):

```371:399:server/src/phone-call.ts
private async handleTelnyxWebhook(event: any, res: ServerResponse): Promise<void> {
  const eventType = event.data?.event_type;
  ...
  switch (eventType) {
    case 'call.answered':
      let streamUrl = `wss://${new URL(this.config.publicUrl).host}/media-stream`;
      ...
      await this.config.providers.phone.startStreaming(callControlId, streamUrl);
```

This is not hierarchical manager-worker or graph-state-agent orchestration; it is one runtime controller reacting to telephony and STT events.

## 4. Tools & External Integrations

- **MCP (Model Context Protocol)**: Exposes phone-related tools to Claude over stdio (`server/src/index.ts:10-13`, `server/src/index.ts:75-131`).
- **Telephony APIs**:
  - Twilio Voice REST + TwiML Media Streams (`server/src/providers/phone-twilio.ts:33-67`, `server/src/providers/phone-twilio.ts:113-124`).
  - Telnyx Call Control API v2 (`server/src/providers/phone-telnyx.ts:35-64`, `server/src/providers/phone-telnyx.ts:70-98`).
- **Speech services**:
  - OpenAI Realtime API for STT over WebSocket (`server/src/providers/stt-openai-realtime.ts:63-93`, `server/src/providers/stt-openai-realtime.ts:207-231`).
  - OpenAI Audio Speech API for TTS (`server/src/providers/tts-openai.ts:31-44`).
  - Optional Kokoro local TTS provider + auto-start support (`server/src/index.ts:22-32`, `server/src/providers/index.ts:90-98`).
- **ngrok**: Public tunnel for provider webhooks to local server, with reconnect and health checks (`server/src/ngrok.ts:23-32`, `server/src/ngrok.ts:95-129`).
- **HTTP + WebSocket server**: Handles `/twiml` webhooks and `/media-stream` audio channel (`server/src/phone-call.ts:89-114`, `server/src/phone-call.ts:245-324`).
- **Webhook security**: Twilio HMAC and Telnyx Ed25519 signature verification + WS token auth (`server/src/webhook-security.ts:22-59`, `server/src/webhook-security.ts:70-117`, `server/src/webhook-security.ts:151-189`).

No browser automation, terminal execution tooling, vector DB, RAG pipeline, or multi-agent router is present.

## 5. Notable Code Walkthrough

- `server/src/index.ts:18-73,75-183` - Main entrypoint: initializes providers/ngrok/server, registers MCP tools, and dispatches tool invocations to `CallManager`; this is the runtime bridge from Claude tool call to telephony actions.
- `server/src/phone-call.ts:70-217,438-547,698-737` - Core orchestration/state machine for active calls, including WebSocket lifecycle, call state maps, speaking/listening loop, transcript wait, and hangup cleanup.
- `server/src/providers/index.ts:48-70,72-124` - Environment-driven provider factory that selects phone/TTS/STT implementations, enabling portability between Twilio/Telnyx and OpenAI/Kokoro.
- `server/src/providers/stt-openai-realtime.ts:55-127,160-199` - Realtime transcription session implementation using OpenAI Realtime events, VAD config, partial/final transcript handling, and reconnect logic.
- `server/src/webhook-security.ts:22-59,70-117,154-189` - Security-critical verification for incoming webhooks and media stream tokens, reducing spoofing/replay risk in exposed webhook endpoints.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** looks inaccurate for this repository. The code does not operate a browser, drive shell tasks, or perform autonomous web/terminal navigation. Instead, it automates a communication workflow: when the LLM decides it needs user input or wants to report progress, it triggers a structured phone-call loop through MCP tools and telephony/STT/TTS backends (`server/src/index.ts:75-131`, `server/src/phone-call.ts:438-547`).

A better category is **Workflow Automation**: it automates escalation and decision capture in long-running AI tasks via phone-based human-in-the-loop interaction.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clean MCP tool surface with focused capability (`initiate/continue/speak/end`) that is easy for an LLM to use (`server/src/index.ts:75-131`).
  - Strong provider abstraction separates telephony, STT, and TTS concerns (`server/src/providers/types.ts:11-146`).
  - Practical production resilience: ngrok reconnects, STT reconnect backoff, graceful shutdown (`server/src/ngrok.ts:132-189`, `server/src/providers/stt-openai-realtime.ts:129-158`, `server/src/index.ts:195-221`).
  - Security controls for webhook and WebSocket authentication are explicitly implemented (`server/src/webhook-security.ts:22-59`, `server/src/webhook-security.ts:151-189`).
  - Low-latency audio path optimization (pre-generated TTS, streaming playback, jitter buffering) is unusually thoughtful for a small plugin (`server/src/phone-call.ts:478-487`, `server/src/phone-call.ts:629-685`).

- **Limitations:**
  - Not a true multi-agent system; no runtime coordination among multiple LLM roles/agents.
  - Core logic is stateful in-memory only; active call state would not survive process restarts (`server/src/phone-call.ts:71-74`).
  - Tight coupling to specific vendors (OpenAI STT mandatory per config validation) limits model/provider flexibility (`server/src/providers/index.ts:146-148`).
  - No formal automated test suite appears in repository layout, which raises regression risk for telephony edge cases.
  - Error handling often returns generic tool-level errors to caller, with limited typed error taxonomy (`server/src/index.ts:176-181`).

- **Research relevance:**
  - Useful evidence for **human-in-the-loop escalation patterns** in agent tooling via voice channels.
  - Illustrates **MCP tool design** for non-text modalities (telephony + real-time audio) in practical agent ecosystems.
  - Demonstrates event-driven orchestration and security tradeoffs when exposing local agent services through public webhooks.
  - Serves as a case study in “agent adjunct infrastructure” rather than multi-agent coordination.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
