---
repo_name: anthropics/courses
url: "https://github.com/anthropics/courses"
stars: 20799
forks: 2133
contributors_count: 16
last_commit_date: "2025-11-13T20:40:50+00:00"
primary_use_case: Workflow Automation
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T10:44:15.961511+00:00"
model: auto
duration_s: 116.2
clone_size_kb: 205633
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`anthropics/courses` is an educational repository of Jupyter notebooks that teach Claude API usage, prompting, evaluations, and tool-calling workflows rather than shipping a single production app. A user typically runs notebooks in folders like `anthropic_api_fundamentals`, `tool_use`, and `prompt_evaluations` to execute example API calls and iterate on prompts. The most “agent-like” material is in the tool-use lessons, where Claude is given tool schemas, requests tool execution, and receives tool results in a loop. The output users get is instructional: runnable examples of Claude calls, tool orchestration patterns, and evaluation utilities.

## 2. Agent Framework & Architecture

This repo does **not** use a dedicated multi-agent framework (no LangGraph, LangChain, AutoGen, CrewAI, or LlamaIndex imports found in code). The core runtime is direct Anthropic SDK calls, e.g. `client.messages.create(...)` in notebooks such as `anthropic_api_fundamentals/01_getting_started.ipynb:182-228`, `tool_use/04_complete_workflow.ipynb:223-231`, and `tool_use/06_chatbot_with_multiple_tools.ipynb:678-681`.

Architecture is mostly **single-model-with-tools**. “Intelligence” is in prompt text plus Claude’s internal tool-selection decisions, while Python handles deterministic execution of requested tools and feeds back `tool_result` messages. Example: `tool_use/06_chatbot_with_multiple_tools.ipynb:545-581` defines multiple tool schemas; `tool_use/06_chatbot_with_multiple_tools.ipynb:645-653` dispatches to local functions/database methods; and chat loops in `tool_use/06_chatbot_with_multiple_tools.ipynb:1029-1068` keep alternating between model calls and tool execution until Claude returns a final text reply.

## 3. Orchestration Pattern

Closest match: **sequential orchestration (single-agent tool loop)**, not multi-agent coordination.

Control flow is request -> model proposes tool -> host executes tool -> host sends tool_result -> model continues.

- Excerpt 1 (`tool_use/04_complete_workflow.ipynb:600-635`):
  > `response = client.messages.create(... tools=[article_search_tool])`  
  > `if(response.stop_reason == "tool_use"):`  
  > `... "type": "tool_result", "tool_use_id": tool_use.id ...`  
  > `response = client.messages.create(... tools=[article_search_tool])`

- Excerpt 2 (`tool_use/06_chatbot_with_multiple_tools.ipynb:1031-1053`):
  > `messages = [{"role": "user", "content": user_message}]`  
  > `while True:`  
  > `response = client.messages.create(... tools=tools, ...)`  
  > `if response.stop_reason == "tool_use":`

This is an iterative single-controller loop in Python, not a manager-worker team of separate LLM agents.

## 4. Tools & External Integrations

- **Anthropic Claude API (primary runtime)**: direct SDK usage via `Anthropic()` and `client.messages.create(...)` in `anthropic_api_fundamentals/01_getting_started.ipynb:182-228`, `tool_use/04_complete_workflow.ipynb:223-231`, and `tool_use/06_chatbot_with_multiple_tools.ipynb:678-681`.
- **Custom function tools exposed to Claude**: JSON-schema tool definitions in `tool_use/04_complete_workflow.ipynb:187-200` and `tool_use/06_chatbot_with_multiple_tools.ipynb:526-581`; tool dispatch in `tool_use/06_chatbot_with_multiple_tools.ipynb:645-653`.
- **Wikipedia API/package**: external knowledge retrieval with `wikipedia.search` and `wikipedia.page` in `tool_use/04_complete_workflow.ipynb:126-132`.
- **Local in-memory “database” simulation**: customer/order retrieval and cancellation methods used as tools in `tool_use/06_chatbot_with_multiple_tools.ipynb` (FakeDatabase sections around `:80-138`, tool dispatch around `:645-653`).
- **AWS Bedrock dependencies (tutorial track)**: `boto3`/`botocore` listed in `prompt_engineering_interactive_tutorial/AmazonBedrock/requirements.txt:1-4`; this is instructional integration material, not a persistent agent platform.
- **No MCP servers / browser automation / vector DB / terminal-agent runtime** observed in the implementation.

## 5. Notable Code Walkthrough

- `tool_use/04_complete_workflow.ipynb:126-132,187-200,600-635` - canonical single-tool workflow: defines a Wikipedia-backed tool, sends tool schema to Claude, detects `stop_reason == "tool_use"`, then returns `tool_result` and gets final answer.
- `tool_use/06_chatbot_with_multiple_tools.ipynb:526-581,645-653,1029-1068` - most representative orchestration notebook; defines multiple business tools, routes tool calls with a Python dispatcher, and runs a continuous chat/tool loop.
- `prompt_evaluations/09_custom_model_graded_prompt_foo/custom_llm_eval.py:5-146` - demonstrates “LLM-as-judge” evaluation pipeline where Claude scores outputs and returns structured JSON used for pass/fail assertions.
- `anthropic_api_fundamentals/01_getting_started.ipynb:182-228` - minimal baseline for how all higher-level notebooks interact with Claude via direct SDK calls.
- `prompt_engineering_interactive_tutorial/AmazonBedrock/requirements.txt:1-4` - shows cross-platform tutorial intent (Anthropic SDK + AWS Bedrock client libraries), relevant for external integration scope.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** is directionally correct for the repo’s most agentic content: it teaches automating multi-step tasks where Claude decides when to call tools and Python executes deterministic actions (lookup, retrieval, cancellation) before resuming model reasoning (`tool_use/06_chatbot_with_multiple_tools.ipynb:1031-1068`).  

However, this repository is broader than one use case: much of it is pedagogy (prompting/evals/fundamentals) rather than a deployable automation product. So the best final category among the allowed options is still **Workflow Automation**, but with the caveat that it is an educational corpus of patterns, not a production automation system.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear end-to-end tool-call loop examples with explicit `tool_use` and `tool_result` handling (`tool_use/04_complete_workflow.ipynb:600-635`).
  - Demonstrates multi-tool routing in a realistic customer-support scenario (`tool_use/06_chatbot_with_multiple_tools.ipynb:526-581,645-653`).
  - Emphasizes prompt iteration and behavioral constraints in conversational workflows (`tool_use/06_chatbot_with_multiple_tools.ipynb:1115-1364`).
  - Includes practical eval patterns (including model-graded evals) to assess prompt/output quality (`prompt_evaluations/09_custom_model_graded_prompt_foo/custom_llm_eval.py:5-146`).

- **Limitations:**
  - No true multi-agent runtime (no planner-worker teams, no graph of distinct agents).
  - Heavy reliance on notebooks; limited modular packaging for production reuse.
  - Naive assumptions are explicitly present (e.g., single tool call at a time comment in `tool_use/06_chatbot_with_multiple_tools.ipynb:747-748`).
  - Security/auth constraints are intentionally weak in demos (explicit warning in `tool_use/06_chatbot_with_multiple_tools.ipynb:65`).
  - Minimal formal orchestration abstractions (no durable state machine, retries, or robust failure-handling framework).

- **Research relevance:**
  - Good evidence for studying **single-agent tool-use orchestration** patterns in practice.
  - Useful for prompt-engineering effects on tool behavior and hallucination control.
  - Useful benchmark material for comparing host-driven tool loops vs. framework-based agent systems.
  - Not suitable as evidence of emergent multi-agent coordination or agent societies.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
