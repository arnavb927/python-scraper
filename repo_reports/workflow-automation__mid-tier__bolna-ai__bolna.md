---
repo_name: bolna-ai/bolna
url: "https://github.com/bolna-ai/bolna"
stars: 626
forks: 271
contributors_count: 30
last_commit_date: "2026-04-20T06:08:50+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T15:32:12.615550+00:00"
model: auto
duration_s: 123.4
clone_size_kb: 36321
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`bolna` is a custom Python orchestration framework for building production-style voice assistants that combine ASR, LLM reasoning, and TTS in real time. A user configures an `Assistant`, adds one or more tasks (most commonly a conversation task), then runs it as an async stream (`assistant.execute()`), receiving event-like chunks and optionally telephony output (`examples/simple_assistant.py:12-52`, `bolna/assistant.py:5-50`). In deployment mode, it also supports hosted-style agent configs with task chains and telephony handlers (`API.md:13-74`, `bolna/providers.py:91-120`). What users get is an end-to-end call/text workflow engine: transcript ingestion, LLM response generation, optional tool/API calls, and synthesized responses back to phone/web channels.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph, CrewAI, AutoGen, or LlamaIndex as its core orchestration runtime. The architecture is a **custom agent runtime** built around `AssistantManager` and `TaskManager`, with provider abstractions and multiple internal agent classes (`bolna/agent_manager/assistant_manager.py:14-90`, `bolna/agent_manager/task_manager.py:78-151`, `bolna/agent_types/__init__.py:1-7`).

At the top level, `AssistantManager.run()` executes configured tasks sequentially (conversation, extraction, summarization, webhook), passing outputs forward (`bolna/agent_manager/assistant_manager.py:57-90`). Inside a conversation task, `TaskManager` creates async queues and runs transcriber/LLM/synthesizer loops concurrently for low-latency streaming (`bolna/agent_manager/task_manager.py:138-150`, `4020-4065`). The “intelligence” lives mostly in agent classes (`StreamingContextualAgent`, `GraphAgent`, `KnowledgeBaseAgent`) and prompts loaded/injected by task manager (`bolna/agent_manager/task_manager.py:1313-1401`).

The strongest “agentic” logic is in `GraphAgent`, where node transitions are decided via deterministic edge expressions first, then an LLM tool-call router fallback (`bolna/agent_types/graph_agent.py:345-368`, `581-638`, `728-867`). However, this is still a single graph-driven agent runtime, not a multi-peer agent swarm.

## 3. Orchestration Pattern

Closest match: **hierarchical + event-driven pipeline orchestration** (manager/worker), with optional graph-style internal routing in one specialized agent.

Control flow is manager-driven and task-sequential:

`bolna/agent_manager/assistant_manager.py:58-64`
```python
for task_id, task in enumerate(self.tasks):
    task_manager = TaskManager(...)
    await task_manager.load_prompt(...)
    task_output = await task_manager.run()
```

Conversation execution is event/stream oriented within each task:

`bolna/agent_manager/task_manager.py:4024-4040`
```python
if self._is_conversation_task():
    tasks = []
    if "transcriber" in self.tools:
        tasks.append(asyncio.create_task(self._listen_transcriber()))
        self.transcriber_task = asyncio.create_task(self.tools["transcriber"].run())
```

For graph agents, control becomes node-state-machine-like inside one agent (`decide_next_node_with_functions`): deterministic transitions then LLM-routed transitions (`bolna/agent_types/graph_agent.py:593-637`).

## 4. Tools & External Integrations

- **LLM providers (OpenAI, Azure, Gemini, LiteLLM-backed families):** wired via `SUPPORTED_LLM_PROVIDERS` and LLM classes (`bolna/providers.py:71-90`, `bolna/llms/litellm.py`, `bolna/llms/openai_llm.py`).
- **ASR/TTS providers:** Deepgram/Azure/etc transcribers and ElevenLabs/Polly/OpenAI/etc synthesizers via provider maps (`bolna/providers.py:43-66`).
- **Telephony I/O (Twilio, Plivo, Exotel, Vobiz, SIP trunk):** input/output handlers selected from maps (`bolna/providers.py:91-120`), instantiated in task manager (`bolna/agent_manager/task_manager.py:754-780`).
- **Function-calling to external HTTP APIs:** dynamic request prep and `aiohttp` execution through `trigger_api()` (`bolna/helpers/function_calling_helpers.py:68-151`), invoked in `TaskManager.__execute_function_call` (`bolna/agent_manager/task_manager.py:2332-2363`).
- **RAG service integration:** external `rag-proxy-server` queried over HTTP (`bolna/helpers/rag_service_client.py:27-204`), consumed by `KnowledgeBaseAgent` and `GraphAgent` (`bolna/agent_types/knowledgebase_agent.py:185-325`, `bolna/agent_types/graph_agent.py:703-719`).
- **Webhook follow-up actions:** `WebhookAgent` posts payloads to arbitrary endpoints (`bolna/agent_types/webhook_agent.py:8-38`).
- **Cloud recording persistence (S3):** call recording uploaded at task completion (`bolna/agent_manager/task_manager.py:4287-4290`).

## 5. Notable Code Walkthrough

- `bolna/agent_manager/task_manager.py:78-151, 526-567, 4020-4355` - Core runtime engine: initializes queues/tools, spins concurrent conversation loops, executes function calls, collects metrics, and handles cleanup.
- `bolna/agent_types/graph_agent.py:45-136, 581-638, 728-867` - Most advanced agent logic: node graph state, deterministic/LLM routing, event-triggered transitions, optional node-level RAG context.
- `bolna/agent_types/knowledgebase_agent.py:30-82, 185-325` - RAG-enabled conversational agent that enriches prompts with retrieved contexts, then streams response generation.
- `bolna/helpers/function_calling_helpers.py:68-151` - Tool execution substrate for HTTP function calls, including templated/body-substituted requests and timeout/error handling.
- `bolna/providers.py:43-120` - Central provider registry that wires external ASR/TTS/LLM/telephony integrations to concrete runtime classes.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is directionally correct. The repo automates end-to-end conversational workflows across channels: listen (ASR) -> reason (LLM agent) -> act (tool/API/webhook/transfer/language-switch) -> respond (TTS/telephony), with follow-up extraction/summarization tasks available in the same assistant pipeline (`bolna/agent_manager/assistant_manager.py:57-90`, `bolna/agent_manager/task_manager.py:1284-1297`, `2047-2418`).  

That said, this is specifically **voice conversation workflow orchestration**, not generic multi-agent planning. The runtime is primarily one active conversational agent per task, coordinated with infrastructure components.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong production-oriented async orchestration for real-time voice loops with interruption handling and latency tracking (`bolna/agent_manager/task_manager.py:343-499`, `4191-4219`).
  - Broad pluggable provider ecosystem (LLM/ASR/TTS/telephony) via clean capability maps (`bolna/providers.py:43-120`).
  - Rich function-calling integration with structured request prep and response logging (`bolna/helpers/function_calling_helpers.py:68-151`).
  - Advanced graph-based conversation option with deterministic + LLM hybrid routing (`bolna/agent_types/graph_agent.py:593-637`).

- **Limitations:**
  - “Multiagent” schema exists but appears only partially wired; no clear runtime routing among multiple peer LLM agents (`bolna/models.py:408-413`, `bolna/agent_manager/task_manager.py:283-557`).
  - Heavy, monolithic `TaskManager` makes behavior hard to reason about and test in isolation (`bolna/agent_manager/task_manager.py` large surface).
  - Security risk from legacy dynamic substitution path using `exec` in API request building (`bolna/helpers/function_calling_helpers.py:86-88`).
  - Limited explicit architectural boundaries between dialogue policy, transport, and tool execution.

- **Research relevance:**
  - Good evidence of **agentic voice orchestration in production constraints** (latency, telephony, interruptions, streaming).
  - Useful example of **hybrid routing** (rule/expression + LLM tool-call routing) in conversational state machines.
  - Valuable for studying **tool-augmented conversational agents** rather than true multi-agent collaboration frameworks.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
