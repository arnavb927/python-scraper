---
repo_name: acon96/home-llm
url: "https://github.com/acon96/home-llm"
stars: 1318
forks: 133
contributors_count: 27
last_commit_date: "2026-04-12T21:10:16+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T15:22:19.506757+00:00"
model: auto
duration_s: 62.3
clone_size_kb: 2955
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`acon96/home-llm` is a Home Assistant custom integration that lets users connect local or self-hosted LLM backends (Ollama, llama.cpp, OpenAI-compatible, Anthropic-compatible) to control smart-home entities via natural language. A user installs the integration in Home Assistant, configures one or more conversation/AI-task entities, and then speaks or types commands like “turn on the living room lights.” The system generates a prompt containing exposed device state, has the model produce tool calls, and executes allowed Home Assistant services. It also supports structured “AI Task” outputs for automation-style data extraction, not just chat replies.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph, LangChain, AutoGen, CrewAI, or LlamaIndex in runtime code. The runtime is a **custom Home Assistant integration** built on Home Assistant’s native conversation/LLM APIs (`homeassistant.helpers.llm`, `conversation`, `ai_task`) with custom backend adapters (`custom_components/llama_conversation/__init__.py:63-73`, `custom_components/llama_conversation/conversation.py:6-14`).

Architecture-wise, the central runtime unit is a `LocalLLMAgent` conversation entity plus `LocalLLMTaskEntity` for structured tasks. Each configured subentry becomes one entity, but these entities are independent and not coordinating as a team (`custom_components/llama_conversation/conversation.py:36-55`, `custom_components/llama_conversation/ai_task.py:35-53`). The “intelligence” mainly lives in prompt templating and tool-call parsing/execution loops (`custom_components/llama_conversation/entity.py:507-604`, `custom_components/llama_conversation/conversation.py:152-216`).

Backend-specific logic is abstracted into `LocalLLMClient` subclasses (Ollama/OpenAI/Anthropic/etc.) that normalize streaming chunks and tool-call formats into Home Assistant content/tool structures (`custom_components/llama_conversation/entity.py:200-333`, `custom_components/llama_conversation/backends/ollama.py:183-245`, `custom_components/llama_conversation/backends/generic_openai.py:122-203`).

## 3. Orchestration Pattern

Closest pattern: **sequential single-agent loop with tool-calling retries** (not multi-agent manager/worker, not graph-state multi-node agents).

Control flow is: build prompt/history → call one model → parse assistant/tool outputs → if tool call occurred, continue another iteration (up to `max_tool_call_iterations`) → return final speech/result.

Example loop trigger and retry logic (`custom_components/llama_conversation/conversation.py:154-209`):

```python
for idx in range(max(1, max_tool_call_iterations)):
    generation_result = await self.client._async_generate(...)
    ...
    if not last_generation_had_tool_calls:
        break
    if idx == max_tool_call_iterations - 1 and max_tool_call_iterations > 0:
        intent_response.async_set_error(...)
```

Tool-call parsing/execution handoff is handled in the stream parser and Home Assistant chat log integration (`custom_components/llama_conversation/entity.py:289-317`):

```python
for raw_tool_call in tool_calls:
    ...
    tool_call, to_say = parse_raw_tool_call(function_content, agent_id)
    if tool_call:
        parsed_tool_calls.append(tool_call)
...
if len(parsed_tool_calls) > 0:
    result.tool_calls = parsed_tool_calls
```

## 4. Tools & External Integrations

- **Home Assistant service-calling tool API**: custom `HassServiceTool` allows controlled service execution (e.g., lights/climate/media/script), wired via `HomeLLMAPI` (`custom_components/llama_conversation/__init__.py:228-307`).
- **Home Assistant native LLM APIs/tools**: optionally fetches configured HA LLM API instance for broader tool access (`custom_components/llama_conversation/conversation.py:99-119`).
- **Ollama API**: official `ollama.AsyncClient` integration for chat/tool calls (`custom_components/llama_conversation/backends/ollama.py:11-12`, `224-233`).
- **OpenAI-compatible chat/responses APIs**: generic adapter over `/chat/completions` and `/responses` (`custom_components/llama_conversation/backends/generic_openai.py:48-73`, `237-432`).
- **Anthropic-compatible Messages API**: supports tool use and vision attachments (`custom_components/llama_conversation/backends/anthropic.py:153-413`).
- **llama.cpp local runtime**: managed backend (plus wheel install/helpers in utilities) (`custom_components/llama_conversation/__init__.py:66`, `custom_components/llama_conversation/utils.py:190-351`).
- **Hugging Face Hub model download**: used for GGUF model retrieval in setup/migration (`custom_components/llama_conversation/utils.py:149-176`, `custom_components/llama_conversation/__init__.py:190-205`).
- **No MCP, browser automation, shell-agent tooling, vector DB/RAG pipeline** detected in runtime integration code.

## 5. Notable Code Walkthrough

- `custom_components/llama_conversation/conversation.py:84-242` - Main conversation runtime: manages chat history, prompt refresh, LLM invocation, tool-call iteration limits, and final Home Assistant `IntentResponse`.
- `custom_components/llama_conversation/entity.py:200-386` - Core stream/non-stream parsing layer that strips “thinking” spans, extracts/normalizes tool calls, and turns backend output into HA assistant/tool content.
- `custom_components/llama_conversation/__init__.py:65-104,228-307` - Integration bootstrap and backend selection; defines/exports the Home Assistant service-execution tool API used by models.
- `custom_components/llama_conversation/ai_task.py:115-260` - Structured AI task pipeline with retries and extraction modes (raw text, strict JSON, or explicit `submit_response` tool call).
- `custom_components/llama_conversation/backends/generic_openai.py:122-203` - Representative external-backend adapter showing request construction, streaming chunk handling, and tool schema injection.

## 6. Use-Case Mapping

The assigned category **`Workflow Automation` is correct**. This project automates smart-home workflows by turning natural-language intent into deterministic Home Assistant service calls under a constrained tool schema (`custom_components/llama_conversation/__init__.py:252-285`). It also supports task-style generation with schema validation/retries (`custom_components/llama_conversation/ai_task.py:201-260`), which fits practical automation pipelines. However, despite the “agent” naming, runtime behavior is primarily a **single LLM agent with iterative tool use**, not a coordinated multi-agent system.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong practical integration with Home Assistant’s existing conversation/LLM interfaces rather than ad-hoc glue code.
  - Multi-backend portability (Ollama, OpenAI-compatible, Anthropic-compatible, llama.cpp) behind a shared client abstraction.
  - Robust tool-call parsing/normalization for heterogeneous model outputs, including malformed-call recovery paths.
  - Structured AI-task mode with schema-based validation and retry loop improves reliability for automation outputs.
  - Prompt generation grounds decisions in live exposed-entity state and optional in-context examples.

- **Limitations:**
  - No true runtime multi-agent coordination (no planner-worker decomposition, role specialization, or inter-agent messaging).
  - Control loop is linear/retry-based; lacks explicit state-machine planning or branching execution graph.
  - Tooling is domain-scoped to Home Assistant services; no broader external action ecosystem (web/search/files/db).
  - Some backend behaviors are lossy/incomplete (e.g., Responses API path currently returns mostly raw text).
  - Safety/policy depth is mostly schema/service allowlists; limited higher-level deliberative safeguards.

- **Research relevance:**
  - Useful evidence for **single-agent tool-use orchestration** in real home-automation environments.
  - Demonstrates practical normalization challenges across backend tool-call formats in production adapters.
  - Good case study for schema-constrained LLM task extraction with retry/error-feedback loops.
  - Less suitable as evidence of multi-agent coordination algorithms, since coordination is absent.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
