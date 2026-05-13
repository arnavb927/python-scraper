---
repo_name: andrewyng/aisuite
url: "https://github.com/andrewyng/aisuite"
stars: 13734
forks: 1446
contributors_count: 33
last_commit_date: "2025-12-15T17:26:01+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:53:07.207540+00:00"
model: auto
duration_s: 95.8
clone_size_kb: 2149
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`aisuite` is a Python (and companion JS) library that gives developers one OpenAI-style interface for many LLM providers, so they can switch models by changing `provider:model` instead of rewriting SDK-specific code. In practice, users instantiate `ai.Client()` and call `client.chat.completions.create(...)` with optional tools, MCP servers, and multi-turn tool execution. The project solves interoperability and orchestration friction across providers like OpenAI, Anthropic, Google, AWS, Cohere, and others, while normalizing messages/responses. It also includes built-in tool-calling loops (`max_turns`) so users can run lightweight agentic workflows without adopting a full agent framework. The output is a provider-normalized completion object plus optional intermediate tool interaction history.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/AutoGen/CrewAI as a core runtime framework; it is a **custom agentic orchestration layer** built around provider adapters and a tool loop. The key framework evidence is direct custom classes and provider factory loading rather than third-party agent graph imports (`aisuite/client.py`, `aisuite/provider.py`, `aisuite/utils/tools.py`).

Architecture-wise, there is one central runtime entrypoint (`Client -> Chat -> Completions`) that routes to a selected provider adapter, then optionally runs iterative tool execution when `max_turns` is set. Tool intelligence lives in: (a) model-side decisions (tool calls), (b) `Tools` schema/validation/execution logic, and (c) MCP adapters that expose external tool servers as Python callables. A representative control loop is in `Completions._tool_runner`:

```249:283:aisuite/client.py
while turns < max_turns:
    response = provider.chat_completions_create(model_name, messages, **kwargs)
    tool_calls = getattr(response.choices[0].message, "tool_calls", None)
    if not tool_calls:
        return response
    results, tool_messages = tools_instance.execute_tool(tool_calls)
    messages.extend([response.choices[0].message, *tool_messages])
    turns += 1
```

So the “intelligence” is mostly centralized: model decides tool invocation; library executes/validates; loop continues until no tool calls or turn budget is exhausted.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker (single-manager loop)** with iterative function-calling (not peer swarm, not graph state machine).

- **Manager:** one LLM completion step per turn.
- **Workers:** registered Python tools and/or MCP tools called by name.
- **Coordinator:** `Completions._tool_runner` appends tool outputs back into the message stream.

Tool registration/execution path:

```234:244:aisuite/client.py
if isinstance(tools, Tools):
    tools_instance = tools
    kwargs["tools"] = tools_instance.tools()
else:
    if not all(callable(tool) for tool in tools):
        raise ValueError("One or more tools is not callable")
    tools_instance = Tools(tools)
    kwargs["tools"] = tools_instance.tools()
```

```332:366:aisuite/utils/tools.py
tool_name = tool_call.function.name
arguments = tool_call.function.arguments
validated_args = param_model(**arguments)
result = tool_func(**validated_args.model_dump())
messages.append({
    "role": "tool",
    "name": tool_name,
    "content": json.dumps(result),
    "tool_call_id": tool_call_id,
})
```

This is effectively a centralized orchestration loop over specialist workers (functions/MCP endpoints).

## 4. Tools & External Integrations

- **LLM provider SDKs (OpenAI, Anthropic, AWS, Google, etc.)**: provider adapters are loaded dynamically via naming convention in `ProviderFactory` (`aisuite/provider.py:34-66`) and concrete provider files (e.g., `aisuite/providers/openai_provider.py:14-51`).
- **MCP (Model Context Protocol) servers (stdio + HTTP):** full client integration in `aisuite/mcp/client.py` (transport setup, handshake, tool discovery, tool calls), then wrapped for tool-calling via `aisuite/mcp/tool_wrapper.py`.
- **Python callable tools as first-class workers:** schema extraction and runtime validation/execution in `aisuite/utils/tools.py`.
- **HTTP transport for MCP:** async JSON-RPC over HTTP/SSE implemented via `httpx` (`aisuite/mcp/client.py:374-455`, `:499-527`).
- **Filesystem/browser-terminal style tool access via MCP servers:** wired in examples/tests by launching `@modelcontextprotocol/server-filesystem` through `npx` (`examples/mcp_config_dict_example.py:30-35`; `tests/mcp/test_llm_e2e.py:64-74`).
- **Audio transcription integrations:** unified audio API and provider pass-through for ASR, e.g., OpenAI whisper-style transcription (`aisuite/client.py:372-503`, `aisuite/providers/openai_provider.py:68-194`).

No built-in vector DB pipeline, browser automation framework (Playwright/Browserbase), or shell executor is implemented directly in core; those capabilities are expected via external tools/MCP servers.

## 5. Notable Code Walkthrough

- `aisuite/client.py:118-357` - Core orchestration engine. Handles model string parsing, provider lazy init, MCP config conversion, and multi-turn tool loop (`max_turns`) with intermediate message tracking.
- `aisuite/utils/tools.py:8-370` - Tool abstraction layer. Infers/constructs JSON schema from Python signatures or MCP schema, validates call args with Pydantic, and executes tool calls into OpenAI-compatible tool-result messages.
- `aisuite/mcp/client.py:34-714` - MCP transport/runtime adapter. Connects to stdio or HTTP MCP servers, performs protocol init, lists tools, wraps callable tools, and executes tool calls over MCP.
- `aisuite/mcp/tool_wrapper.py:19-152` - Converts MCP tool schema into callable Python wrappers with signatures/docstrings so they can be consumed by the `Tools` manager transparently.
- `tests/mcp/test_llm_e2e.py:45-382` - Real provider integration tests showing practical agentic workflows: LLM chooses tools, MCP filesystem is invoked, and multi-turn loops complete tasks; includes multi-server prefixing scenarios.

## 6. Use-Case Mapping

Assigned label `Browser / Terminal Use` is **partially** supported but not the best primary category for the core repo. The library itself is a general orchestration layer for model/tool workflows; terminal/browser behavior appears mainly through external MCP servers (e.g., filesystem server via `npx`) rather than native browser/terminal control primitives.

A better top-level fit is **Workflow Automation**: the core implementation focuses on orchestrating multi-step LLM + tool interactions across providers (`aisuite/client.py:211-291`, `:332-355`) and normalizing tool execution patterns (`aisuite/utils/tools.py`). Browser/terminal use is an optional downstream tool capability via MCP integrations, not the central architecture.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Unified cross-provider API with dynamic adapter loading keeps integration friction low (`aisuite/provider.py`).
  - Clean, reusable multi-turn tool-calling loop with bounded turns (`aisuite/client.py`).
  - Strong MCP integration (stdio + HTTP) broadens external tool ecosystem without bespoke glue (`aisuite/mcp/client.py`).
  - Tool schema handling is practical: signature inference + Pydantic validation + OpenAI-format conversion (`aisuite/utils/tools.py`).
  - Good end-to-end tests for real LLM + MCP behavior, not only mocks (`tests/mcp/test_llm_e2e.py`).

- **Limitations:**
  - No explicit multi-agent role graph/planner-worker abstraction; orchestration is mostly single-controller loop.
  - Control flow is linear/turn-based; no native DAG/state-machine execution, retries, or advanced scheduling.
  - Limited built-in observability for agent traces beyond intermediate message collection.
  - Heavy reliance on provider/tool behavior; fewer guardrails for complex failure recovery across turns.
  - Browser/terminal actions are not first-class built-ins; depend on external MCP servers.

- **Research relevance:**
  - Useful as evidence of a lightweight, production-oriented “agentic wrapper” pattern over heterogeneous LLM APIs.
  - Demonstrates practical protocol-mediated tool ecosystems (MCP) integrated into LLM loops.
  - Illustrates centralized orchestration of heterogeneous workers (Python tools + MCP services) under one model policy.
  - Relevant for studies on interoperability layers versus full agent frameworks in real developer workflows.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
