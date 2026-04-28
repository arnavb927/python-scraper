---
repo_name: inclusionAI/AWorld
url: "https://github.com/inclusionAI/AWorld"
stars: 1181
forks: 122
contributors_count: 47
last_commit_date: "2026-04-22T06:31:22+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T12:54:15.863804+00:00"
model: auto
duration_s: 116.9
clone_size_kb: 255696
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`AWorld` is a Python framework and CLI for building and running LLM-powered agents as coordinated multi-agent systems, rather than a single chatbot. In practice, a user runs `aworld-cli` (interactive or task mode) or creates a `Task`/`Swarm` programmatically, and the runtime executes agent decisions, tool calls, and inter-agent handoffs (`aworld-cli/src/aworld_cli/main.py:693-750`, `aworld/runner.py:155-188`). The core problem it solves is orchestrating complex agent workflows (planning, delegation, tool use, and memory) with reusable topology patterns like workflow, team, handoff, and hybrid swarms (`aworld/core/agent/swarm.py:19-46`, `aworld/core/agent/swarm.py:387-555`). Output is a task response stream/final result plus structured traces and tool/agent events.

## 2. Agent Framework & Architecture

This repo does **not** use CrewAI/LangGraph/AutoGen as its primary runtime. The agent framework is mostly **custom AWorld orchestration** (`BaseAgent`, `LLMAgent`, `Swarm`, event handlers), with OpenAI-compatible model providers and MCP integrations (`aworld/core/agent/base.py:75-95`, `aworld/agents/llm_agent.py:142-175`, `aworld/core/agent/swarm.py:29-46`, `aworld/models/openai_provider.py:32-43`, `aworld/mcp_client/server.py:27-59`).  
LangChain appears only in a retrieval utility (`langchain_text_splitters`) rather than in agent orchestration (`aworld/core/context/amni/retrieval/chunker/smart_chunker.py:6-8`).

Architecture is centered on:
- **Agent runtime class hierarchy:** `BaseAgent` defines lifecycle (`async_run`, `async_policy`) and handoff/tool capability fields (`tool_names`, `handoffs`, `mcp_servers`) (`aworld/core/agent/base.py:75-93`, `aworld/core/agent/base.py:266-341`).
- **LLM decision layer:** `LLMAgent` builds prompt/messages, transforms available tools/agents into callable function specs, calls model, parses tool calls into `ActionModel`s, and dispatches results (`aworld/agents/llm_agent.py:336-443`, `aworld/agents/llm_agent.py:779-894`).
- **Multi-agent topology layer:** `Swarm` + builders (`WorkflowBuilder`, `HandoffBuilder`, `TeamBuilder`, `HybridBuilder`) construct the agent graph and delegation edges (`aworld/core/agent/swarm.py:844-984`, `aworld/core/agent/swarm.py:1006-1216`).

“Intelligence” is distributed across (a) prompts/system prompt templates in agent configs and context prompt formatting, and (b) runtime routers that decide whether each LLM action is a tool call, handoff, or terminal answer (`aworld/agents/llm_agent.py:1287-1301`, `aworld/runners/handler/agent.py:184-219`).

## 3. Orchestration Pattern

Closest match: **hybrid manager-worker + graph orchestration** (with configurable workflow/handoff/team/hybrid graphs).  
The graph is explicitly built and validated in `Swarm`/builders, then runtime handlers route messages according to graph type (`aworld/core/agent/swarm.py:139-166`, `aworld/runners/handler/agent.py:290-299`).

Control flow example 1 (graph build + explicit handoff edges):

```1074:1090:aworld/core/agent/swarm.py
# agent handoffs graph build.
agent_graph = AgentGraph(GraphBuildType.HANDOFF.value, root_agent=self.root_agent)
for agent_pair in valid_agent_pair:
    ...
    agent_graph.add_edge(pair[0], pair[1])
    # explicitly set handoffs in the agent
    pair[0].handoffs.append(pair[1].id())
```

Control flow example 2 (runtime router by swarm mode):

```290:299:aworld/runners/handler/agent.py
async def _stop_check(self, action: ActionModel, message: Message) -> AsyncGenerator[Message, None]:
    if GraphBuildType.TEAM.value == self.swarm.build_type or GraphBuildType.HYBRID.value == self.swarm.build_type:
        async for event in self._team_stop_check(action, message):
            yield event
    elif GraphBuildType.HANDOFF.value == self.swarm.build_type:
        async for event in self._handoff_stop_check(action, message):
            yield event
    else:
        async for event in self._workflow_stop_check(action, message):
            yield event
```

So execution is not a single sequential chain; it is topology-aware routing with manager-style (`TeamSwarm`) and peer handoff (`HandoffSwarm`) options.

## 4. Tools & External Integrations

- **MCP servers (core integration):** clients for stdio/SSE/streamable-http MCP transports and tool invocation (`aworld/mcp_client/server.py:239-323`, `aworld/mcp_client/server.py:349-409`, `aworld/mcp_client/server.py:431-487`).
- **Sandboxed MCP tool orchestration:** dynamic tool listing, permission filtering by allowed MCP servers, per-server execution/reuse, metadata injection (`aworld/sandbox/run/mcp_servers.py:65-99`, `aworld/sandbox/run/mcp_servers.py:242-309`, `aworld/agents/llm_agent.py:410-429`).
- **Built-in terminal MCP server:** safe shell execution with timeout/safety checks (`aworld/sandbox/tool_servers/terminal/src/terminal.py:93-115`, `aworld/sandbox/tool_servers/terminal/src/terminal.py:148-174`, `aworld/sandbox/tool_servers/terminal/src/terminal.py:317-333`).
- **Built-in filesystem MCP server:** read/write/edit/search/list operations with allowed-directory constraints (`aworld/sandbox/tool_servers/filesystem/src/main.py:68-123`, `aworld/sandbox/tool_servers/filesystem/src/main.py:125-209`, `aworld/sandbox/tool_servers/filesystem/src/main.py:290-320`).
- **OpenAI-compatible model provider:** OpenAI/AsyncOpenAI SDK based calls, streaming and retry logic (`aworld/models/openai_provider.py:73-111`, `aworld/models/openai_provider.py:422-497`, `aworld/agents/llm_agent.py:1028-1178`).
- **Function-tool adapters:** non-MCP Python functions exposed in MCP-like schema (`aworld/tools/function_tools.py:34-61`, `aworld/tools/function_tools.py:228-245`, `aworld/tools/function_tools.py:435-463`).
- **Git tool wrappers:** structured `git_status`, `git_diff`, `git_log`, `git_commit` callable by agents (`aworld/tools/git_tools.py:43-126`, `aworld/tools/git_tools.py:128-188`, `aworld/tools/git_tools.py:190-289`).

## 5. Notable Code Walkthrough

- `aworld/core/agent/swarm.py:29-166` - Defines MAS topology primitives and initialization path (`Swarm`, graph build type, root/ordered agents), making this the structural center of multi-agent behavior.
- `aworld/runners/handler/agent.py:184-299` - Runtime dispatcher that separates tool actions vs agent handoffs and routes to workflow/team/handoff stop-check logic; this is where graph semantics become execution semantics.
- `aworld/agents/llm_agent.py:340-443` - Converts available tools/agents/MCP capabilities into model-callable specs and enforces per-agent tool visibility, directly shaping each agent’s action space.
- `aworld/agents/llm_agent.py:779-894` - Main inference loop: build LLM input, call model (stream/non-stream), parse `tool_calls` into actions, and either finish or trigger tool execution.
- `aworld/sandbox/run/mcp_servers.py:242-540` - Practical tool runtime: per-server dispatch, parameter injection, retries/timeouts, and conversion of MCP responses to framework `ActionResult`.

## 6. Use-Case Mapping

The assigned label **Code Generation** is partially valid (the platform can run coding agents with terminal/filesystem/git tools), but the codebase itself is broader and more foundational: it is primarily an **agent workflow orchestration framework** for many domains (research, web tasks, coding, evaluation, skills, and task automation). The strongest evidence is that core abstractions are topology/routing/scheduling/tool-runtime primitives rather than code-synthesis-specific logic (`aworld/core/agent/swarm.py`, `aworld/runners/handler/agent.py`, `aworld/sandbox/run/mcp_servers.py`).  
Given the provided taxonomy, a better fit is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Supports multiple coordination paradigms (workflow, handoff, team, hybrid) in one runtime (`aworld/core/agent/swarm.py:19-27`, `aworld/core/agent/swarm.py:1327-1332`).
  - Clear separation between decision (LLM), orchestration (handlers/graph), and execution (tools/MCP).
  - Strong tool substrate: MCP transports + sandboxed execution + built-in terminal/filesystem servers.
  - Agent-as-tool and subagent delegation are first-class (`handoffs`, spawn-subagent tooling).
  - Includes streaming outputs, hooks, memory, and evaluation infrastructure for production-style agent systems.

- **Limitations:**
  - High complexity and many subsystems increase operational/debug burden; behavior is spread across handlers, runners, and context layers.
  - Heavy reliance on model function-calling correctness; malformed tool calls still require defensive parsing/recovery.
  - Safety controls exist, but terminal/file capabilities are powerful and policy quality depends on deployment configuration.
  - Some advanced features appear experimental/optional, making defaults and best-practice paths harder to infer.
  - Framework breadth may hinder reproducibility for narrowly defined tasks without careful config pinning.

- **Research relevance:**
  - Good evidence for studying **multi-agent topology effects** (manager-worker vs handoff vs hybrid) within one codebase.
  - Useful for analyzing **tool-mediated agency** via MCP and constrained tool visibility per agent.
  - Demonstrates practical **event-driven MAS runtime engineering** (message routing, retries, async cleanup, hooks).
  - Relevant for empirical work on **agent delegation and subagent spawning** under real execution constraints.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
