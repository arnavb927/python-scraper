---
repo_name: llamastack/llama-stack
url: "https://github.com/llamastack/llama-stack"
stars: 8341
forks: 1303
contributors_count: 231
last_commit_date: "2026-04-22T13:34:51+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T11:16:49.713010+00:00"
model: auto
duration_s: 116.9
clone_size_kb: 137098
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`llamastack/llama-stack` (now branded in-code as OGX) is a composable API server that exposes OpenAI-compatible Responses/Chat APIs plus storage, tool, and vector capabilities behind one runtime. In practice, users run the server via the CLI (`ogx run ...`) and send API requests to `/v1/responses`, `/v1/tools`, `/v1/vector_stores`, etc., while choosing providers through config (`src/ogx/cli/stack/run.py:30-57`, `src/ogx/core/server/server.py:222-358`). The core value is provider abstraction: a single app can route inference, tool runtime, safety, and RAG/vector operations across built-in and remote adapters. The “agentic” behavior is implemented as iterative model+tool orchestration in the Responses implementation, not as a separate autonomous agent framework (`src/ogx/providers/inline/responses/builtin/responses/openai_responses.py:1052-1217`).

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/AutoGen/CrewAI as its runtime orchestration framework. I found no such imports in `src/`; LangChain/LangGraph appear only in compatibility tests (`tests/integration/responses/test_langchain_responses.py:8-12`, `tests/integration/responses/test_langgraph_responses.py:11-13`).

The actual implementation is a **custom orchestrator** centered on `OpenAIResponsesImpl` and `StreamingResponseOrchestrator`. Request handling builds chat context, processes tool descriptors (including MCP), then iteratively calls inference and executes tool calls until completion/limits (`src/ogx/providers/inline/responses/builtin/responses/openai_responses.py:1091-1170`, `src/ogx/providers/inline/responses/builtin/responses/streaming.py:469-709`).

“Intelligence” lives in the model plus control logic: tool-choice normalization, MCP tool listing/approval gates, guardrail checks, max-iteration/max-tool-call limits, and conversation/background persistence (`streaming.py:1791-1900`, `streaming.py:1576-1707`, `openai_responses.py:617-824`). This is closer to a robust tool-calling runtime than a multi-role agent society.

## 3. Orchestration Pattern

Closest match: **sequential iterative loop (single-agent tool-calling controller)**, with event-streaming and background queue support.

Control flow is: preprocess context/tools → call model → separate tool calls → execute tools → append tool outputs → loop again until no calls or limits reached.

```476:486:src/ogx/providers/inline/responses/builtin/responses/streaming.py
while True:
    if (
        self.max_output_tokens is not None
        and self.accumulated_builtin_output_tokens >= self.max_output_tokens
    ):
        ...
        break
```

```675:686:src/ogx/providers/inline/responses/builtin/responses/streaming.py
# Execute tool calls and coordinate results
async for stream_event in self._coordinate_tool_execution(...):
    yield stream_event
messages = next_turn_messages
if not function_tool_calls and not non_function_tool_calls:
    break
```

Tool execution itself is centralized in a single executor that dispatches by tool type (MCP, web search, file search, generic tool runtime), not by distinct collaborating agents (`src/ogx/providers/inline/responses/builtin/responses/tool_executor.py:325-392`).

## 4. Tools & External Integrations

- **MCP servers (Model Context Protocol):** list/invoke tools over streamable HTTP/SSE, auth header handling, per-request session reuse (`src/ogx/providers/utils/tools/mcp.py:390-509`, `src/ogx/providers/remote/tool_runtime/model_context_protocol/model_context_protocol.py:12-71`).
- **Web search providers:** Brave, Bing, Tavily as remote tool-runtime adapters (`src/ogx/providers/registry/tool_runtime.py:43-75`).
- **Wolfram Alpha tool runtime:** computational external tool integration (`src/ogx/providers/registry/tool_runtime.py:76-86`).
- **Built-in file search / RAG runtime:** ingestion to vector stores, chunk retrieval, query generation, and context assembly (`src/ogx/providers/inline/tool_runtime/file_search/file_search.py:125-305`).
- **Vector stores/backends:** exposed through `VectorIO`; file-search runtime depends on vector store search/query APIs (`file_search.py:170-223`, `tool_executor.py:128-257`).
- **Inference provider abstraction:** Responses orchestrator calls generic inference API for chat completions with optional reasoning (`streaming.py:527-573`).
- **Safety/guardrails:** input/output guardrail checks integrated into streaming generation (`streaming.py:412-419`, `streaming.py:1235-1249`).
- **Conversation/response persistence & background jobs:** queue-based background processing and resumable response storage (`openai_responses.py:151-258`, `openai_responses.py:825-1038`).

## 5. Notable Code Walkthrough

- `src/ogx/providers/inline/responses/builtin/responses/openai_responses.py:115-217,1052-1217`  
  Main Responses implementation: request validation, previous-response/conversation reconstruction, streaming orchestration setup, persistence, and background-mode execution.

- `src/ogx/providers/inline/responses/builtin/responses/streaming.py:221-299,397-709,1387-1523`  
  Core orchestration loop for model streaming + tool-call coordination; handles tool-choice transformations, MCP approvals/listings, and terminal response states.

- `src/ogx/providers/inline/responses/builtin/responses/tool_executor.py:51-127,325-392,434-540`  
  Unified tool dispatcher that executes MCP/file/web/generic tools and converts raw tool outputs into both streamed output items and next-turn tool messages.

- `src/ogx/providers/utils/tools/mcp.py:81-149,390-443,471-509`  
  MCP transport/session abstraction with protocol fallback and session caching, which is critical for practical multi-call tool sessions.

- `src/ogx/providers/inline/tool_runtime/file_search/file_search.py:188-305,338-365`  
  RAG-oriented built-in tool runtime implementing query generation, vector-store chunk retrieval, ranking/truncation, and context packaging for the model.

## 6. Use-Case Mapping

The repository clearly supports the assigned **RAG + Agents** functionality at the API/runtime level: file ingestion + vector retrieval (`file_search.py`), then iterative tool-augmented response generation (`streaming.py`, `tool_executor.py`). However, the “agents” part is primarily a **single assistant with tool orchestration**, not multiple coordinated LLM agents (no manager/worker teams, no agent graph runtime in core code).  

So for strict taxonomy, I would classify the primary implemented behavior as **Workflow Automation** (tool-call orchestration, approvals, background execution, persistence), with strong RAG capabilities as a major sub-feature.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong OpenAI-compatible response-event model with detailed streaming semantics (`streaming.py`).
  - Practical tool integration layer spanning MCP + multiple web search providers + built-ins (`tool_runtime.py`, `mcp.py`).
  - Production-minded controls: guardrails, max iterations/tool calls/output tokens, background queueing (`openai_responses.py`, `streaming.py`).
  - Good state continuity: previous response recovery, conversation syncing, incremental persistence (`openai_responses.py:275-350,530-616`).
  - RAG pipeline is integrated end-to-end (ingest/query/context formatting) rather than demo-only (`file_search.py`).

- **Limitations:**
  - No true runtime multi-agent coordination (planner/worker/swarm); mostly single-loop controller.
  - Orchestration policy is mostly hard-coded branching, not declarative graphs/plans; extensibility may be harder.
  - Some tool-runtime paths rely on broad exception handling and stringified errors; fine-grained failure semantics are uneven.
  - File-search runtime contains legacy patterns and mixed concerns (upload/chunk/query/context formatting in one module).
  - “Agent” terminology in logs/APIs can overstate actual architectural multi-agent behavior.

- **Research relevance:**
  - Good evidence for **industrial-grade tool-calling orchestration** patterns in LLM middleware.
  - Useful reference for MCP session management and protocol-fallback implementation details.
  - Illustrates how RAG retrieval can be fused into a unified Responses loop with streaming observability.
  - Supports studies on guardrail/tool-approval governance in production LLM serving stacks.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
