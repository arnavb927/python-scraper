---
repo_name: guidance-ai/guidance
url: "https://github.com/guidance-ai/guidance"
stars: 21402
forks: 1156
contributors_count: 84
last_commit_date: "2026-04-10T12:34:07+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T10:41:03.401452+00:00"
model: auto
duration_s: 95.3
clone_size_kb: 50639
uses_mas: no
final_use_case: Workflow Automation
---
I’ve finished the code inspection and have enough evidence for architecture, control flow, and integrations. Next I’ll provide the final Markdown report with the exact section structure and classification block.## 1. Overview

`guidance` is a Python library for writing constrained LLM programs, not an out-of-the-box autonomous agent app. Users instantiate a model backend (for example `guidance.models.OpenAI(...)`), compose prompts/roles/constraints with the Guidance DSL (`with system()/user()/assistant(): ...`, `gen(...)`, JSON/regex grammars), and execute it to get model outputs plus captured structured values. The core problem it solves is making LLM generation controllable and verifiable via grammars, typed tool schemas, and interpreter-backed execution rather than free-form prompting alone. In practice, a user runs Python code that incrementally builds a model state and can interleave generation with tool calls.

## 2. Agent Framework & Architecture

This repository does **not** use LangGraph, LangChain, AutoGen, CrewAI, or LlamaIndex as its runtime framework. The architecture is custom: an AST + interpreter system where Guidance constructs (`RoleStart`, `RuleNode`, `ToolCallNode`, etc.) are executed by model-specific interpreters (`guidance/models/_base/_interpreter.py:32-105`, `guidance/models/_openai_base.py:251-543`, `guidance/models/_engine/_interpreter.py:16-156`).

“Intelligence” primarily lives in:
- the prompt program the user writes via Guidance decorators/DSL (`guidance/_guidance.py:17-42`, `guidance/library/_gen.py:13-151`, `guidance/library/_role.py:8-63`),
- the model provider itself (OpenAI/Azure/etc.),
- and deterministic runtime handling in interpreters (tool-call parsing, schema enforcement, grammar constraints).

There is tool-use support, but it is still a **single assistant policy loop**, not multiple cooperating agents. `ToolCallNode.from_tools(...)` wraps Python callables as tool definitions (`guidance/_ast.py:619-643`), and the OpenAI interpreter executes returned tool calls and appends tool results to the chat state (`guidance/models/_openai_base.py:496-533`).

## 3. Orchestration Pattern

Closest match: **other (single-agent, interpreter-driven prompt program)**.

Control flow is linear and stateful: AST node -> interpreter method -> model/provider call -> optional tool execution -> append to state. There is no planner-worker graph, no agent registry, and no peer-to-peer agent messaging.

Example flow 1 (DSL triggers tool-call node):
`guidance/library/_gen.py:109-116`
```python
@guidance(stateless=False, dedent=False)
def tool_gen(lm):
    return lm + ToolCallNode.from_tools(
        tools=tools,
        tool_choice=tool_choice,
        parallel_tool_calls=False,
        plaintext_regex=regex,
    )
```

Example flow 2 (interpreter executes tool calls and reinserts results):
`guidance/models/_openai_base.py:511-532`
```python
for tool_call in final_tool_calls.values():
    if isinstance(tool_call, FunctionCall):
        name = tool_call.function.name
        tool = tools[name]
        args = json.loads(tool_call.function.arguments)
        result = tool.call(**args)
    ...
    self.state.messages.append(ToolCallResult(tool_call_id=tool_call.id, content=result_str))
```

## 4. Tools & External Integrations

- **OpenAI Chat Completions API**: wired in `guidance/models/_openai.py:15-72` and executed via streaming wrapper in `guidance/models/_openai_base.py:228-248`, `:326-334`.
- **Azure OpenAI / Azure AI Inference**: wired in `guidance/models/_azureai.py:30-61`, `:76-156`, `:188-277`.
- **LiteLLM router over multiple providers** (OpenAI, Azure, Gemini, Anthropic, Groq, Mistral, hosted vLLM, etc.): `guidance/models/experimental/_litellm.py:62-105`, `:265-274`.
- **Local model inference via Hugging Face Transformers**: `guidance/models/_transformers.py:345-443`, `:581-626`.
- **Local model inference via llama.cpp / ONNX Runtime GenAI** (through model exports): `guidance/models/__init__.py:4-8`.
- **Python function tools (user-defined callables)**: schemas and adapters in `guidance/_tools.py:29-71`, `:95-115`, and node wiring in `guidance/_ast.py:619-643`.
- **Tool execution loop (runtime function invocation)**: OpenAI interpreter executes and injects tool results into message state in `guidance/models/_openai_base.py:496-533`.
- **RAG/vector DB integrations**: no first-class vector-store/retriever wiring found in package code (`guidance/*.py`), despite tutorial notebooks mentioning RAG patterns.

## 5. Notable Code Walkthrough

- `guidance/_guidance.py:17-42,129-193` - Defines the `@guidance` decorator and wraps user functions into `GuidanceFunction` objects, enabling stateless/stateful grammar construction and recursive rule handling.
- `guidance/library/_gen.py:13-151` - Core generation primitive; routes standard token generation and, when `tools` are provided, emits `ToolCallNode` for tool-enabled interaction.
- `guidance/_ast.py:613-650` - `ToolCallNode` definition and `from_tools` constructor that converts Python callables/Tool objects into validated runtime tool definitions.
- `guidance/models/_openai_base.py:294-334,336-543` - Main OpenAI execution engine: streams model deltas, accumulates content/tool calls, invokes mapped Python tools, and appends tool-result messages.
- `guidance/models/_base/_model.py:100-150,199-266` - Immutable model state machine; applies AST nodes through interpreters and manages captures/state propagation across turns.

## 6. Use-Case Mapping

The assigned label (`RAG + Agents`) is only partially accurate. The repo strongly supports **agent-like tool use** (single assistant calling tools) and structured prompt workflows, but I did not find native multi-agent coordination (no manager-worker graphs, no swarm runtime, no multi-agent scheduler). I also did not find built-in retriever/vector-store pipelines in core code; “RAG” appears more as tutorial usage than framework primitive.

Better fit: **Workflow Automation**. Guidance is a programmable control layer for deterministic, constrained LLM workflows with optional tool execution, rather than a dedicated multi-agent orchestration framework.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong constrained generation architecture (grammar/regex/JSON) integrated into runtime interpreters (`guidance/models/_base/_interpreter.py:67-95`).
  - Clean tool abstraction that converts Python callables to schemas (`guidance/_tools.py:33-71`, `:176-203`).
  - Provider-flexible backend design (OpenAI, Azure, LiteLLM, local engines) with mostly unified model API (`guidance/models/__init__.py:1-20`).
  - Immutable model-state pattern improves reproducibility and traceability (`guidance/models/_base/_model.py:199-210`).
  - Streaming and token-level tracing support useful for debugging and evaluation (`guidance/models/_openai_base.py:341-405`).

- **Limitations:**
  - No true multi-agent runtime orchestration; tool use is single-assistant loop.
  - Local engine path currently lacks tool calling (`guidance/models/_engine/_interpreter.py:154-156`).
  - Parallel tool calls are explicitly disabled/TODO in generation API (`guidance/library/_gen.py:114`).
  - Some provider features are partial or endpoint-specific (regex/grammar/json support varies in LiteLLM adapter).
  - RAG infrastructure is not first-class in core package code (no built-in vector-store/retriever modules).

- **Research relevance:**
  - Good evidence for **constrained decoding as an alternative to fragile prompt-only control** in agentic workflows.
  - Useful case study of **tool-call grounding through typed schemas and runtime execution hooks**.
  - Demonstrates a **custom AST/interpreter architecture** for LLM programming, distinct from graph-based agent frameworks.
  - Relevant for studies on **single-agent tool-augmented orchestration**, but not for multi-agent coordination claims.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
