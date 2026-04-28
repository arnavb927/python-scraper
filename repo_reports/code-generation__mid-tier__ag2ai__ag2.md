---
repo_name: ag2ai/ag2
url: "https://github.com/ag2ai/ag2"
stars: 4432
forks: 592
contributors_count: 479
last_commit_date: "2026-04-22T21:47:45+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 6
architecture_labels: [LangChain, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents]
generated_at: "2026-04-27T12:17:55.290736+00:00"
model: auto
duration_s: 134.4
clone_size_kb: 220635
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`ag2ai/ag2` is an LLM agent framework (formerly AutoGen) for building agents that talk to each other, call tools, and execute multi-step workflows. Users typically instantiate `ConversableAgent`/`AssistantAgent` (or the newer `autogen.beta.Agent`), configure model clients, then run `run_group_chat(...)`, `initiate_chat(...)`, or `agent.ask(...)` to execute tasks. At runtime, AG2 handles message routing, speaker/agent selection, tool invocation, and optional human-in-the-loop checkpoints. The output is a full interaction trace (messages/events, usage/cost, summary), not just a single model response.

## 2. Agent Framework & Architecture

This repo is **primarily AG2/AutoGen’s own framework**, not LangGraph/CrewAI/LlamaIndex at core runtime. The main runtime classes are in `autogen/agentchat/*` (`ConversableAgent`, `GroupChat`, `GroupChatManager`) and `autogen/beta/*` (`Agent`, event stream, middleware, tool executor).  
Evidence: `autogen/agentchat/conversable_agent.py`, `autogen/agentchat/groupchat.py`, `autogen/beta/agent.py`.

Architecture is split across two stacks:

- **Classic stack (`agentchat`)**: agents are stateful conversational objects with pluggable reply functions (`register_reply`), LLM calls, tool calls, and optional code execution (`conversable_agent.py:538+`, `2465+`, `2754+`). Multi-agent runs are coordinated by `GroupChatManager`, which loops rounds, broadcasts messages, selects next speaker, and triggers replies (`groupchat.py:1302-1433`).
- **Beta stack (`autogen.beta`)**: async-first, event-driven loop using `Stream`, middleware, and tool executor. `Agent._execute` wires LLM calls + tool execution via event subscriptions; `_execute_turn` repeatedly executes tool calls until final response (`beta/agent.py:605-754`).
- **Delegation/subagents** in beta are explicit tools (`subagent_tool`) that call `run_task(...)`, emit `TaskStarted/Completed/Failed`, and return results to parent agents (`beta/tools/subagents/subagent_tool.py:23-86`, `run_task.py:28-94`).

“Intelligence” lives in system prompts, dynamic prompt hooks, LLM-based speaker selection, and handoff conditions (context-based and LLM-evaluated transitions).

## 3. Orchestration Pattern

**Closest pattern: hierarchical (manager-worker), with dynamic routing.**

The `GroupChatManager` controls the loop and decides who speaks next; workers are the member agents. Routing can be round-robin/random/manual/LLM-auto/custom function (`groupchat.py:85-97`, `660-689`, `1302-1378`). In auto mode, AG2 even runs a nested 2-agent selector-validator chat to choose one speaker (`groupchat.py:799-880`).

Example control-loop excerpt (`autogen/agentchat/groupchat.py:1332-1378`):
```python
for i in range(groupchat.max_round):
    self._last_speaker = speaker
    groupchat.append(message, speaker)
    for agent in groupchat.agents:
        if agent != speaker:
            self.send(message, agent, request_reply=False, silent=True)
    speaker = groupchat.select_speaker(speaker, self)
    reply = speaker.generate_reply(sender=self)
```

Example beta turn loop (`autogen/beta/agent.py:744-753`):
```python
async def _execute_turn(event: BaseEvent, context: Context) -> ModelResponse:
    async with context.stream.get(ModelResponse) as result:
        await context.send(event)
        message: ModelResponse = await result

    while message.tool_calls and not message.response_force:
        async with context.stream.get(ModelResponse) as result:
            await context.send(message.tool_calls)
            message = await result
```

## 4. Tools & External Integrations

- **LLM providers** (OpenAI/Anthropic/Gemini/etc. via config clients/mappers): wired under `autogen/beta/config/*` and classic `OpenAIWrapper` usage in `conversable_agent.py:2519+`.
- **Function/tool calling**: tool calls parsed and executed through `_function_map` in `conversable_agent.py:2754-2814`.
- **Code execution**:
  - Classic agent code execution (`generate_code_execution_reply`) in `conversable_agent.py:2629-2677`.
  - Experimental Python tool in `autogen/tools/experimental/code_execution/python_code_execution.py:21-85`.
  - Beta built-in `CodeExecutionTool` export in `autogen/beta/tools/builtin/__init__.py:5-28`.
- **Shell/terminal execution**: experimental shell executor with command/path safety filters in `autogen/tools/experimental/shell/shell_tool.py:25-279`; beta `ShellTool` exported in `beta/tools/builtin/__init__.py`.
- **MCP integration**:
  - Classic MCP client/proxy and toolkit conversion in `autogen/mcp/mcp_client.py:15-209`.
  - Beta MCP server schema tool in `autogen/beta/tools/builtin/mcp_server.py:19-76`.
- **Web and browsing tools**:
  - Beta `WebSearchTool` / `WebFetchTool` exports in `beta/tools/builtin/__init__.py`.
  - Experimental browser automation via `browser_use` in `autogen/tools/experimental/browser_use/browser_use.py:74-144`.
- **Messaging platforms / external services**: Slack/Telegram/Discord/google/tavily/firecrawl/etc. under `autogen/tools/experimental/*` (wired as Tool classes).

## 5. Notable Code Walkthrough

- `autogen/agentchat/conversable_agent.py:136-364, 2465-2814`  
  Core agent runtime: message memory, reply-function chain, LLM call generation, function/tool execution, and optional code execution. This file defines how a single agent “thinks and acts.”

- `autogen/agentchat/groupchat.py:48-177, 504-701, 1183-1433`  
  Multi-agent coordinator data model + manager loop. It enforces transitions/eligibility, selects next speaker (including LLM-auto selection), and runs the round-based group conversation.

- `autogen/agentchat/group/multi_agent_chat.py:43-125, 213-283`  
  High-level entrypoints (`initiate_group_chat`, `run_group_chat`) that prepare pattern-driven orchestration and run group chats in sync/async background execution modes.

- `autogen/beta/agent.py:605-754`  
  New event-driven async execution pipeline: middleware wrapping, tool schema resolution, stream subscriptions, and iterative tool-call handling until final model response.

- `autogen/beta/tools/subagents/subagent_tool.py:23-86` and `run_task.py:28-94`  
  Canonical multi-agent delegation in beta: a parent agent invokes a child agent as a tool, with task lifecycle events and variable/dependency propagation.

## 6. Use-Case Mapping

Assigned label was **Code Generation**, but the codebase itself is broader and better characterized as **Workflow Automation**.  
Reason: code generation is one supported behavior (e.g., `AssistantAgent` default coding prompt and code execution hooks), but the dominant architecture is generalized multi-agent orchestration: routing, handoffs, group patterns, tool ecosystems, safeguards, event streaming, MCP/web/browser integrations, and HITL. In practice, AG2 is an AgentOS/framework that automates arbitrary multi-step workflows, of which coding is one scenario.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Mature multi-agent orchestration primitives (group manager, patterns, handoffs, nested chats).
  - Clear separation of classic and new beta runtime, with beta offering a clean async event architecture.
  - Rich tool ecosystem (shell, code exec, web, MCP, browser) with unified tool-call handling.
  - Strong extensibility via middleware, observers, hooks, and custom speaker selection.
  - Practical operational features: safeguards, HITL, resumable chats, usage/cost accounting.

- **Limitations:**
  - Architectural complexity/duplication: classic `agentchat` and `beta` coexist, raising migration and maintenance overhead.
  - Some APIs are deprecated (e.g., swarm helpers), so users may face churn.
  - Safety model depends heavily on configuration discipline; dangerous capabilities (shell/code) exist by design.
  - Determinism/reproducibility across multi-agent flows is limited due to LLM-driven routing.
  - Very large surface area makes minimal, opinionated “golden path” less obvious for newcomers.

- **Research relevance:**
  - Strong reference implementation for **manager-mediated multi-agent coordination** in production-style code.
  - Useful empirical artifact for studying **tool-augmented agent loops** and iterative tool-call execution.
  - Demonstrates **hybrid routing** (rule/context + LLM-based handoffs) in one framework.
  - Provides concrete event traces/hooks suitable for observability and evaluation studies.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
