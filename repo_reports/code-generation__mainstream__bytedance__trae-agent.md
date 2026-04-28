---
repo_name: bytedance/trae-agent
url: "https://github.com/bytedance/trae-agent"
stars: 11388
forks: 1241
contributors_count: 52
last_commit_date: "2026-02-05T11:21:00+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation]
generated_at: "2026-04-27T11:07:51.010119+00:00"
model: auto
duration_s: 85.4
clone_size_kb: 7435
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`bytedance/trae-agent` is a Python CLI agent that takes a natural-language software task (for example, “fix this bug” or “add tests”), runs an LLM in a tool-using loop, and applies changes in a target codebase. Users run commands like `trae-cli run "..." --working-dir ...`, and the agent iteratively calls tools (bash, file editing, JSON editing, optional MCP tools) until it decides the task is complete. The runtime also supports interactive mode, Docker execution mode, and trajectory recording for debugging/research. In practice, this is an autonomous software-engineering workflow runner rather than just a chat assistant.

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework**, not LangGraph/LangChain/CrewAI/AutoGen. The core loop is implemented directly in `BaseAgent`, with provider adapters in `utils/llm_clients` and custom tool abstractions in `tools` (`trae_agent/agent/base_agent.py:24-353`, `trae_agent/tools/base.py:74-245`, `trae_agent/utils/llm_clients/llm_client.py:27-87`). I did not find imports of LangGraph, LangChain, CrewAI, AutoGen, or LlamaIndex in the runtime path.

Architecture is primarily **single-agent + tool calling**. `AgentType` currently exposes only `TraeAgent`, which subclasses `BaseAgent` and supplies prompt, completion rules, and default tools (`trae_agent/agent/agent.py:10-48`, `trae_agent/agent/trae_agent.py:30-119`, `trae_agent/prompt/agent_prompt.py:4-53`). The “intelligence” is split between: (a) a large system prompt; (b) model-side tool/function calling; and (c) deterministic control logic in `_run_llm_step` and `_tool_call_handler`.

The LLM backend is pluggable (OpenAI, Anthropic, Azure, OpenRouter, Ollama, Doubao, Google) through a wrapper that normalizes responses and tool calls (`trae_agent/utils/llm_clients/llm_client.py:15-63`, `trae_agent/utils/llm_clients/openai_compatible_base.py:109-215`, `trae_agent/utils/llm_clients/anthropic_client.py:53-153`).

## 3. Orchestration Pattern

Closest match: **sequential ReAct-style workflow automation loop** (single controller agent invoking tools), with optional parallel execution of multiple tool calls in one step.

Control flow is explicit: LLM step -> check completion -> tool calls -> feed tool results back -> next step (`trae_agent/agent/base_agent.py:163-237`).

```164:236:trae_agent/agent/base_agent.py
while step_number <= self._max_steps:
    ...
    llm_response = self._llm_client.chat(messages, self._model_config, self._tools)
    ...
    if self.llm_indicates_task_completed(llm_response):
        ...
    else:
        tool_calls = llm_response.tool_calls
        return await self._tool_call_handler(tool_calls, step)
```

Tool execution strategy is selected by config (`parallel_tool_calls`), then results are appended as new messages for the next LLM turn (`trae_agent/agent/base_agent.py:331-352`).

```331:340:trae_agent/agent/base_agent.py
if self._model_config.parallel_tool_calls:
    tool_results = await self._tool_caller.parallel_tool_call(tool_calls)
else:
    tool_results = await self._tool_caller.sequential_tool_call(tool_calls)
...
for tool_result in tool_results:
    message = LLMMessage(role="user", tool_result=tool_result)
    messages.append(message)
```

## 4. Tools & External Integrations

- **Shell/terminal execution (`bash` tool):** persistent subprocess session for command execution (`trae_agent/tools/bash_tool.py:19-159`, `trae_agent/tools/bash_tool.py:162-247`).
- **Filesystem editing tools:** structured file edit and JSON edit tools for create/view/replace/insert operations (`trae_agent/tools/edit_tool.py:27-133`, `trae_agent/tools/json_edit_tool.py`).
- **MCP servers (Model Context Protocol):** agent can discover MCP tool schemas over stdio and wrap them as callable tools (`trae_agent/utils/mcp_client.py:39-71`, `trae_agent/tools/mcp_tool.py:8-58`, `trae_agent/agent/trae_agent.py:65-100`).
- **LLM provider APIs:** OpenAI-compatible clients + Anthropic-specific client wiring with function/tool calling (`trae_agent/utils/llm_clients/openai_compatible_base.py:124-166`, `trae_agent/utils/llm_clients/anthropic_client.py:69-95`).
- **Docker execution environment:** selected tools are executed inside container with path translation (`trae_agent/tools/docker_tool_executor.py:57-155`, `trae_agent/agent/base_agent.py:49-73`).
- **Code Knowledge Graph (CKG):** local AST indexing using tree-sitter and SQLite, exposed as a tool for symbol lookup (`trae_agent/tools/ckg_tool.py:14-133`, `trae_agent/tools/ckg/ckg_database.py:148-197`, `trae_agent/tools/ckg/ckg_database.py:534-575`).
- **External services not natively implemented:** MCP HTTP/WebSocket transports are declared but currently `NotImplementedError` (`trae_agent/utils/mcp_client.py:47-51`).

## 5. Notable Code Walkthrough

- `trae_agent/agent/base_agent.py:147-353` - Core runtime loop (LLM call, completion check, tool execution, reflection, trajectory recording). This is the orchestration heart of the project.
- `trae_agent/agent/trae_agent.py:30-259` - Task-specific agent specialization: default tools, system prompt binding, MCP discovery, completion gating via `task_done` and optional non-empty patch enforcement.
- `trae_agent/tools/base.py:74-245` - Tool abstraction and executor; defines uniform schemas and sequential/parallel invocation behavior used by all tools.
- `trae_agent/utils/llm_clients/openai_compatible_base.py:109-215` - Provider-agnostic OpenAI-style client path that converts tool definitions to API schema and parses tool calls back into internal `ToolCall`.
- `trae_agent/utils/mcp_client.py:26-105` - MCP connection/discovery lifecycle; dynamically imports remote MCP tools into the agent’s toolset at runtime.

## 6. Use-Case Mapping

The repo clearly supports the assigned **Code Generation** use case (and adjacent bug-fixing/refactoring) by giving an LLM direct code-manipulation and execution tools, then iterating until completion (`trae_agent/cli.py:126-383`, `trae_agent/prompt/agent_prompt.py:10-42`). However, the implemented behavior is broader than generation: it executes end-to-end engineering workflows (inspect, run commands/tests, edit, verify, finalize). So the better category is **Workflow Automation** rather than pure Code Generation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clean, readable custom orchestration loop; easy to inspect and modify (`trae_agent/agent/base_agent.py`).
  - Strong tool-centric design with uniform schema abstraction across providers (`trae_agent/tools/base.py`, `.../openai_compatible_base.py`).
  - Broad provider support and configurable model backends (`trae_agent/utils/llm_clients/llm_client.py`).
  - Practical execution environments: local, Docker, and MCP-extended tools (`trae_agent/tools/docker_tool_executor.py`, `trae_agent/utils/mcp_client.py`).
  - Built-in trajectory recording useful for debugging and research reproducibility (`trae_agent/utils/trajectory_recorder.py`, agent integration points).

- **Limitations:**
  - Runtime is effectively single-agent; no planner-worker/team coordination graph in main CLI flow (`trae_agent/agent/agent.py`).
  - Heavy reliance on prompt instructions for process discipline (e.g., “must reproduce bug”) rather than hard constraints (`trae_agent/prompt/agent_prompt.py`).
  - MCP transport support is partial (stdio only; HTTP/WebSocket not implemented) (`trae_agent/utils/mcp_client.py:47-51`).
  - Tool safety/governance is limited (powerful bash/edit tools with minimal policy sandboxing outside Docker mode).
  - Some platform assumptions in tool docs/behavior (e.g., Unix-style path messaging in editor tool).

- **Research relevance:**
  - Good reference for **single-agent tool-use orchestration** in software engineering tasks.
  - Useful for studying **provider-agnostic tool-calling normalization** across API ecosystems.
  - Suitable baseline for experiments on **test-time scaling via iterative tool loops** and max-step budgets.
  - Helpful for work on **trajectory logging/evaluation pipelines** (including the patch-selector evaluation submodule).

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
