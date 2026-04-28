---
repo_name: GetStream/Vision-Agents
url: "https://github.com/GetStream/Vision-Agents"
stars: 7674
forks: 627
contributors_count: 25
last_commit_date: "2026-04-22T19:26:04+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T11:57:05.801264+00:00"
model: auto
duration_s: 92.7
clone_size_kb: 243247
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`GetStream/Vision-Agents` is a Python framework for building real-time voice/video AI agents that join live calls, process audio/video streams, and respond through LLMs plus STT/TTS providers. A user typically runs an agent script (for example via `Runner(...).cli()`), which creates an `Agent`, connects to Stream/Twilio transport, and handles conversational turns automatically. The repo includes a core runtime (`agents-core`) and many provider plugins (OpenAI, Gemini, Anthropic, Deepgram, ElevenLabs, Twilio, etc.). In practice, developers get a deployable “AI participant” for calls, phone bots, or multimodal assistants, with optional function/tool calling and optional retrieval plugins.

## 2. Agent Framework & Architecture

This is **not** built on LangGraph/CrewAI/AutoGen/LlamaIndex as its main runtime. The core is a **custom agent framework** (`vision_agents.core`) with an event bus, pluggable LLM/STT/TTS/turn-detection modules, and provider adapters. Evidence: central classes `Agent`, `LLM`, and `AgentLauncher` are in `agents-core/vision_agents/core/...`, and orchestration is implemented directly in methods like `Agent.setup_event_handling()` and `Agent._on_turn_ended()` (`agents-core/vision_agents/core/agents/agents.py:301-336`, `:1586-1645`).

Architecturally, a single `Agent` instance composes:
- transport (`edge`),
- one LLM backend (or realtime multimodal model),
- optional STT/TTS/turn detection,
- optional processors and MCP servers.

The “intelligence” primarily lives in:
1) provider LLM prompts/instructions (`LLM.set_instructions`, `Agent.instructions`),  
2) tool/function-calling loops in provider implementations (`plugins/openai/.../openai_llm.py:233-277`, `plugins/gemini/.../gemini_llm.py:285-367`),  
3) event-driven turn handling in `Agent` (audio->STT->turn end->LLM->TTS).

There is one notable external framework usage: `plugins/turbopuffer/.../turbopuffer_rag.py` uses LangChain components for embeddings/text splitting, but this is for RAG indexing/retrieval, not agent orchestration.

## 3. Orchestration Pattern

Closest match: **event-driven pipeline** (with sequential turn flow inside each conversation). It is not a multi-agent manager/worker graph; it is one agent reacting to media/transcript events.

Control flow is explicitly documented and wired via event subscriptions:

```301:311:agents-core/vision_agents/core/agents/agents.py
    Agent event handling:

    - STT: AudioReceivedEvent -> STTTranscriptEvent -> TurnCompleted -> LLMResponseCompletedEvent -> TTSAudioEvent
    - Eager: AudioReceivedEvent -> STTTranscriptEvent -> EagerTurnCompleted -> LLMResponseCompletedEvent
        - > if TurnCompleted -> TTSAudioEvent
```

```1599:1638:agents-core/vision_agents/core/agents/agents.py
        # When turn detection is enabled, trigger LLM response when user's turn ends.
        ...
        if not transcript.strip():
            return
        ...
        llm_turn = LLMTurn(...)
        self._pending_turn = llm_turn
        task = asyncio.create_task(
            self.simple_response(transcript, event.participant)
        )
```

Tool calls are then orchestrated as iterative sub-steps inside a single LLM turn (execute tools, send outputs back, possibly repeat), e.g. in OpenAI provider (`plugins/openai/vision_agents/plugins/openai/openai_llm.py:249-276`).

## 4. Tools & External Integrations

- **LLM providers**: OpenAI, Gemini, Anthropic, AWS Bedrock, HuggingFace, etc. wired through plugin-specific `LLM` classes (e.g. `plugins/openai/vision_agents/plugins/openai/openai_llm.py`, `plugins/gemini/vision_agents/plugins/gemini/gemini_llm.py`).
- **Function/tool calling runtime**: generic function registry + concurrent execution in core (`agents-core/vision_agents/core/llm/function_registry.py`, `agents-core/vision_agents/core/llm/llm.py:289-348`).
- **MCP servers**: remote/local MCP integration; tools from MCP are converted and registered into LLM tool registry (`agents-core/vision_agents/core/mcp/mcp_manager.py:29-47`, `:113-147`).
- **Realtime transport/video call infra**: Stream edge transport and RTC flows (`agents-core/vision_agents/core/agents/agents.py` + `plugins/getstream/.../stream_edge_transport.py`).
- **Telephony**: Twilio media stream webhook/websocket integration in example and plugin (`examples/03_phone_and_rag_example/inbound_phone_and_rag_example.py:70-132`, `plugins/twilio/...`).
- **Speech services**: Deepgram STT, ElevenLabs TTS, plus others via plugins (`examples/01_simple_agent_example/simple_agent_example.py:48-51`).
- **RAG backends**:
  - Gemini File Search managed store (`plugins/gemini/vision_agents/plugins/gemini/file_search.py`),
  - TurboPuffer hybrid retrieval with embeddings/BM25 (`plugins/turbopuffer/vision_agents/plugins/turbopuffer/turbopuffer_rag.py`).
- **Observability/serving**: FastAPI session server and metrics endpoints (`agents-core/vision_agents/core/runner/http/api.py`).

## 5. Notable Code Walkthrough

- `agents-core/vision_agents/core/agents/agents.py:82-1706`  
  Main runtime class. It binds transport + LLM + STT/TTS + processors, subscribes to events, and executes turn logic from incoming audio to generated responses.

- `agents-core/vision_agents/core/llm/llm.py:45-367`  
  Abstract LLM contract and shared tool-execution utilities (`_dedup_and_execute`, `_run_one_tool`) used by provider implementations for structured function calling.

- `plugins/openai/vision_agents/plugins/openai/openai_llm.py:121-354`  
  Concrete OpenAI adapter that streams responses, extracts tool calls, executes tools concurrently, and loops through multiple tool rounds.

- `agents-core/vision_agents/core/mcp/mcp_manager.py:9-158`  
  MCP integration layer connecting MCP servers, listing/registering tools, and exposing them to the agent’s LLM function registry.

- `examples/03_phone_and_rag_example/inbound_phone_and_rag_example.py:136-192`  
  Practical RAG+voice assembly: initializes Gemini or TurboPuffer retrieval, wires a search function/tool into the LLM, and runs a Twilio-connected phone agent.

## 6. Use-Case Mapping

The repository **does implement RAG + Agents**, but as an **optional pattern** rather than the central runtime abstraction. The core product is a real-time agent orchestration SDK for voice/video workflows; RAG appears in plugins/examples (Gemini File Search and TurboPuffer) and is injected as tools/functions into a single conversational agent (`examples/03_phone_and_rag_example/inbound_phone_and_rag_example.py:170-183`).

So the upstream assignment (“RAG + Agents”) is partially correct for documented examples, but the broader codebase better fits **Workflow Automation**: event-driven orchestration of live multimodal interactions across transports, tools, and provider plugins.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong custom event-driven runtime for low-latency audio/video conversational loops (`agents.py` turn/event wiring).
  - Provider-agnostic plugin architecture with many production integrations (LLM/STT/TTS/transport).
  - Unified function-calling abstraction with concurrent tool execution and iterative tool rounds (`llm.py`, provider adapters).
  - MCP tool ingestion built into core, enabling external capability extension without rewriting LLM adapters.
  - Good deployment surface: CLI run mode and FastAPI session server with lifecycle/metrics support (`runner.py`, `runner/http/api.py`).

- **Limitations:**
  - Runtime is mostly **single-agent per session**; no explicit inter-agent coordination protocol (planner-worker/society patterns absent).
  - Some quality issues in core style/robustness (broad exception handling appears in multiple hot paths, e.g. `agents.py`/provider loops).
  - Tool-calling behavior is provider-specific and somewhat duplicated across plugins, increasing maintenance surface.
  - RAG is fragmented across plugins/examples rather than a unified first-class retrieval orchestration layer.
  - Long, complex `Agent` class mixes many responsibilities (media IO, orchestration, metrics, conversation sync), making formal reasoning harder.

- **Research relevance:**
  - Useful evidence for **event-driven single-agent orchestration** in real-time multimodal systems.
  - Demonstrates practical integration of tool-calling loops and MCP in production-style agent SDKs.
  - Illustrates tradeoffs between framework-general abstractions and provider-specific adapter logic.
  - Relevant for studying voice/video agent engineering, but not a benchmark example of true multi-agent coordination.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
