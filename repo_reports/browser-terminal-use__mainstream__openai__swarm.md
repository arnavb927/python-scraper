---
repo_name: openai/swarm
url: "https://github.com/openai/swarm"
stars: 21367
forks: 2276
contributors_count: 15
last_commit_date: "2026-04-15T17:10:28+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:44:39.693225+00:00"
model: auto
duration_s: 83.5
clone_size_kb: 1545
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`openai/swarm` is a lightweight Python framework for orchestrating multiple LLM agents via tool-calling and handoffs, built directly on OpenAI Chat Completions. A user typically instantiates `Swarm()`, defines one or more `Agent` objects with instructions and Python functions, and then calls `client.run(...)` (for example in `examples/basic/bare_minimum.py:1-13` and `swarm/repl/repl.py:60-88`). The runtime loops model responses, executes requested tools, and can switch the active agent when a tool returns another `Agent` (`swarm/core.py:71-87`, `swarm/core.py:279-287`). The result is a conversational workflow where specialized agents route tasks and call local business logic without a heavy graph framework.

## 2. Agent Framework & Architecture

This repo uses a **custom orchestration framework** (`swarm`) plus the **OpenAI Python SDK** (`from openai import OpenAI` in `swarm/core.py:8`, `examples/support_bot/main.py:4`). I found no LangChain/LangGraph/AutoGen/CrewAI imports in code search.

Architecture-wise, the core abstractions are in `swarm/types.py:14-41`: `Agent` (name/model/instructions/functions/tool settings), `Result` (tool return envelope with optional context and agent handoff), and `Response`. The main intelligence loop is in `Swarm.run` / `run_and_stream` (`swarm/core.py:231-292`, `swarm/core.py:139-229`): it builds system instructions, sends chat completion requests with JSON tool schemas, executes returned tool calls, appends tool outputs to history, updates context variables, and optionally changes active agent.

Prompt-level intelligence lives in each agent’s `instructions` (string or callable with context variables) (`swarm/core.py:42-47`, `examples/airline/configs/agents.py:32-46`). Routing/planning is mostly delegated to the model via those prompts plus transfer tools that return other agents (`examples/triage_agent/agents.py:31-47`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker with tool-based handoff** (plus lightweight swarm-like peer transfer). A “triage” agent commonly routes to specialist agents, and specialists can transfer back.

Control flow in core runtime:

```255:287:swarm/core.py
while len(history) - init_len < max_turns and active_agent:
    completion = self.get_chat_completion(...)
    message = completion.choices[0].message
    ...
    if not message.tool_calls or not execute_tools:
        break

    partial_response = self.handle_tool_calls(
        message.tool_calls, active_agent.functions, context_variables, debug
    )
    history.extend(partial_response.messages)
    context_variables.update(partial_response.context_variables)
    if partial_response.agent:
        active_agent = partial_response.agent
```

Handoff is implemented by tool functions returning another `Agent`:

```71:80:swarm/core.py
def handle_function_result(self, result, debug) -> Result:
    match result:
        case Result() as result:
            return result
        case Agent() as agent:
            return Result(
                value=json.dumps({"assistant": agent.name}),
                agent=agent,
            )
```

And used explicitly in examples:

```31:47:examples/triage_agent/agents.py
def transfer_back_to_triage():
    return triage_agent

def transfer_to_sales():
    return sales_agent

def transfer_to_refunds():
    return refunds_agent

triage_agent.functions = [transfer_to_sales, transfer_to_refunds]
sales_agent.functions.append(transfer_back_to_triage)
```

## 4. Tools & External Integrations

- **OpenAI Chat Completions API**: core model execution and tool-calling in `swarm/core.py:58-69`, `swarm/core.py:260-268`.
- **OpenAI Embeddings API**: used in support-bot retrieval flow (`client.embeddings.create`) in `examples/support_bot/main.py:23-29` (also mirrored in `examples/support_bot/customer_service.py:25-31`).
- **Qdrant vector DB**: `qdrant_client.QdrantClient(host="localhost")` and `.search(...)` in `examples/support_bot/main.py:11`, `examples/support_bot/main.py:31-37`.
- **SQLite**: local transactional backend for personal shopper workflow in `examples/personal_shopper/database.py:1-11`, plus SQL operations throughout `examples/personal_shopper/main.py:14-83`.
- **CLI/terminal I/O loop**: interactive `input(...)`/`print(...)` loop for agent conversations in `swarm/repl/repl.py:69-87`.
- **No browser automation wiring in core**: I did not find Playwright/Browserbase/Selenium-style integrations in runtime modules.

## 5. Notable Code Walkthrough

- `swarm/core.py:26-292` - Core orchestration engine: converts Python callables to tools, sends completions, executes tool calls, merges context, and handles inter-agent handoff.
- `swarm/types.py:14-41` - Defines the contract for agents and tool outputs (`Agent`, `Response`, `Result`), which is the backbone of all runtime behavior.
- `examples/triage_agent/agents.py:16-47` - Canonical multi-agent routing example showing a triage agent delegating to sales/refunds and specialists handing back.
- `examples/airline/configs/agents.py:32-92` - More realistic hierarchical policy flow with context-aware instruction functions and multi-stage routing (triage -> modification -> cancel/change).
- `swarm/repl/repl.py:60-88` - Demonstrates how users actually run sessions: persistent message history plus active-agent updates across turns.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially true. Terminal interaction exists (REPL-style chat loop in `swarm/repl/repl.py:69-87`), but this repo is primarily an **agent orchestration/workflow framework** for routing and tool execution across business tasks (refunds, airline support, support KB triage). There is no substantial browser-control stack in the core code. A better primary category is **Workflow Automation**, with optional examples touching **RAG + Agents** via Qdrant (`examples/support_bot/main.py:3-37`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Minimal, readable core loop; easy to understand and extend (`swarm/core.py`).
- Elegant handoff mechanism (tool returns `Agent`) enables composable multi-agent routing.
- Supports both streaming and non-streaming execution paths in one interface.
- Context-variable injection pattern allows dynamic instructions and stateful workflows.
- Example suite covers multiple orchestration motifs (triage, customer service, airline flows).

- **Limitations:**
- Orchestration is model-driven and prompt-heavy; limited explicit deterministic planning/verification.
- Tool schema generation is basic (`function_to_json`) and may under-spec complex types (`swarm/util.py:31-87`).
- No built-in persistence/observability layer beyond message history in memory.
- Some examples appear inconsistent/stale (e.g., `from swarm.agents import create_triage_agent` in `examples/personal_shopper/main.py:6`, but no corresponding module in `swarm/`).
- Security/sandboxing policy for tool execution is left to user-defined Python functions.

- **Research relevance:**
- Useful evidence for lightweight function-calling-based MAS orchestration without graph frameworks.
- Demonstrates practical agent handoff semantics as first-class runtime behavior.
- Good case study of prompt-routed hierarchical delegation in customer-support domains.
- Illustrates how “multi-agent” can be implemented as dynamic role transfer over a single chat history.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
