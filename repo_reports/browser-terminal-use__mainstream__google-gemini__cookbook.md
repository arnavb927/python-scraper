---
repo_name: google-gemini/cookbook
url: "https://github.com/google-gemini/cookbook"
stars: 17065
forks: 2603
contributors_count: 97
last_commit_date: "2026-04-22T16:05:36+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 9
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T09:13:22.891547+00:00"
model: auto
duration_s: 106.5
clone_size_kb: 389279
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`google-gemini/cookbook` is a large example repository showing how to build applications with the Gemini API, mostly as runnable notebooks plus a few scripts. A user typically runs a notebook (Colab or local Jupyter), sets an API key, and executes end-to-end flows such as tool-calling assistants, browser-connected agents, RAG pipelines, and ADK-based agent apps. The outputs are practical working demos: chat loops, tool invocations, grounded answers, screenshots/parsed web content, and safety-filtered agent responses. Rather than one unified product, the repo is a reference collection of implementation patterns for integrating Gemini into real workflows.

## 2. Agent Framework & Architecture

The code uses **Google’s own SDK stack**, not LangGraph/CrewAI as primary runtime frameworks. The main agentic frameworks visible in code are:

- **Google ADK** (`google.adk.agents`, `google.adk.runners`, `google.adk.plugins`) in `examples/google-adk/Getting_started_with_ADK.ipynb:189-193` and `examples/gemini_google_adk_model_guardrails.ipynb:673-826`.
- **Gemini Python SDK tool-calling** (`client.chats.create(... tools=...)`) in `examples/Agents_Function_Calling_Barista_Bot.ipynb:337-356`.
- A **custom ReAct loop** (hand-rolled orchestration + stop-sequence function-calling imitation) in `examples/Search_Wikipedia_using_ReAct.ipynb:499-787`.

Architecture is mostly **single-agent + tools** per notebook. The “intelligence” lives primarily in system instructions/prompts and tool schemas (for example the barista prompt constraints and required `confirm_order` → `place_order` flow in `examples/Agents_Function_Calling_Barista_Bot.ipynb:256-264`).

There is at least one true **multi-agent** pattern: in the ADK guardrails notebook, a main task agent is wrapped by a plugin that calls a second LLM “judge” agent on user input/tool output/model output (`examples/gemini_google_adk_model_guardrails.ipynb:556-741`, `811-826`). That is coordinated at runtime via ADK callbacks.

## 3. Orchestration Pattern

Closest match: **Other (tool-centric workflow orchestration with occasional hierarchical guardrail supervision)**.

Most examples are sequential control loops where one LLM decides tool calls, then Python executes the tool and returns results. Example from browser live stream handling:

`examples/Browser_as_a_tool.ipynb:274-307`
```python
async def stream_response(stream, *, tool=None):
  async for msg in stream.receive():
    if text := msg.text:
      print(text, end='')
    elif tool_call := msg.tool_call:
      for fc in tool_call.function_calls:
        tool_result = tool(**fc.args) if tool else 'ok'
        tool_response = types.LiveClientToolResponse(...)
        await stream.send(input=tool_response)
```

In the guardrails notebook, control is closer to **hierarchical manager-worker**: a safety plugin mediates all stages and delegates safety judgment to another LLM agent before allowing continuation.

`examples/gemini_google_adk_model_guardrails.ipynb:703-741`
```python
if await self._is_unsafe(wrapped):
    invocation_context.session.state["is_user_prompt_safe"] = False
...
async def after_tool_callback(...):
    wrapped = f"<tool_output>\n{result_str}\n</tool_output>"
    if await self._is_unsafe(wrapped):
        return {"error": "Tool output blocked by safety filter"}
```

## 4. Tools & External Integrations

- **Gemini API / Google GenAI SDK**: core model calls and chat/tooling across notebooks, e.g. `examples/Agents_Function_Calling_Barista_Bot.ipynb:350-353`, `examples/Browser_as_a_tool.ipynb:268-274`.
- **Google ADK runtime** (Agent, Runner, Session, Plugins): `examples/google-adk/Getting_started_with_ADK.ipynb:189-193, 283-291`; `examples/gemini_google_adk_model_guardrails.ipynb:668-741`.
- **Function tools (custom Python functions)** for workflow operations: coffee ordering functions in `examples/Agents_Function_Calling_Barista_Bot.ipynb:120-172`; state transition tool in `examples/google-adk/Getting_started_with_ADK.ipynb:220-241`.
- **Browser automation via Selenium + Chrome WebDriver**: screenshot/browser tool in `examples/Browser_as_a_tool.ipynb:555-607`.
- **Google Search grounding tool** in Live API config: `examples/Browser_as_a_tool.ipynb:268-271`.
- **Wikipedia external API/library** for ReAct tools: `examples/Search_Wikipedia_using_ReAct.ipynb:586-624, 643-666`.
- **Google Cloud Model Armor** optional safety integration in ADK flow: `examples/gemini_google_adk_model_guardrails.ipynb:1016-1036, 1216-1231`.

## 5. Notable Code Walkthrough

- `examples/gemini_google_adk_model_guardrails.ipynb:556-826` - Defines a dedicated `safety_judge_agent`, then a `LlmAsAJudgeSafetyPlugin` that intercepts user/tool/model stages and blocks unsafe content. This is the clearest coordinated multi-agent runtime in the repo.
- `examples/Browser_as_a_tool.ipynb:274-307, 555-607, 693-714` - Implements end-to-end tool-calling for live browsing: stream handler catches function calls, executes browser tools, and feeds responses back to the model.
- `examples/Agents_Function_Calling_Barista_Bot.ipynb:256-264, 337-356, 504-513` - A practical single-agent workflow app: constrained system prompt + domain tools + chat loop until `place_order` completes.
- `examples/Search_Wikipedia_using_ReAct.ipynb:499-521, 586-624, 726-787` - Custom ReAct class that emulates function calling via stop tokens and dispatches `search`/`lookup`/`finish` actions against Wikipedia.
- `examples/google-adk/Getting_started_with_ADK.ipynb:220-241, 254-291` - Minimal ADK pattern: one agent, one tool, in-memory session state, and runner-managed execution lifecycle.

## 6. Use-Case Mapping

The assigned category **Browser / Terminal Use** is only partially reflected. There is meaningful browser-tool usage (`examples/Browser_as_a_tool.ipynb`) including Selenium-driven page interaction, but terminal-use/CLI-agent behavior is not a central architectural theme.

From the codebase as a whole, a better fit is **Workflow Automation**: most agentic examples orchestrate business/task workflows (order-taking, state transitions, safety gating, scripted research loops) through tool calls and structured prompts. So I would reclassify primary use case to **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Demonstrates multiple concrete orchestration styles (plain tool-calling, ADK runner/plugin callbacks, custom ReAct loop).
  - Includes a real multi-agent safety design (task agent + judge agent) instead of only prompt-level claims.
  - Strong practical integrations (browser automation, search grounding, cloud safety services).
  - Reproducible notebook-first implementations with clear runnable flow from setup to interaction.
  - Good coverage of “agent + tools” patterns that developers can adapt quickly.

- **Limitations:**
  - Not a cohesive single system; architecture is fragmented across many independent notebooks.
  - Most examples are single-agent; multi-agent coordination appears in limited subsets.
  - Heavy notebook format makes code reuse/testing/packaging less rigorous than a library/service repo.
  - Prompt/instruction quality is central, but systematic evaluation harnesses are sparse in most recipes.
  - Browser/tool demos often include environment-specific setup assumptions (e.g., Colab/Linux for Chromium).

- **Research relevance:**
  - Useful evidence for **applied agent engineering patterns** in production-oriented SDK ecosystems (Gemini + ADK).
  - Shows a concrete implementation of **LLM-as-a-judge supervisory architecture** in runtime callbacks.
  - Illustrates **tool-mediated grounding** and ReAct-like reasoning/action loops without heavyweight orchestration frameworks.
  - Suitable as a reference corpus for studying tradeoffs between notebook prototypes and robust agent system design.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
