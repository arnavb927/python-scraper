---
repo_name: 01-ai/langcrew
url: "https://github.com/01-ai/langcrew"
stars: 114
forks: 8
contributors_count: 3
last_commit_date: "2025-10-31T15:18:07+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-04-27T17:01:44.702191+00:00"
model: auto
duration_s: 83.2
clone_size_kb: 16184
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`01-ai/langcrew` is a Python framework for building and running coordinated LLM agent workflows, with a CrewAI-like API on top of LangGraph execution. A user typically defines multiple `Agent` and `Task` objects, then runs them via `Crew.kickoff()`/`invoke()` to execute a multi-step pipeline (e.g., research -> synthesis -> delivery). Under the hood, it compiles those definitions into LangGraph state graphs, supports sync/async/streaming execution, and adds memory, handoff, MCP tools, and human-in-the-loop controls. The repo also includes a full-stack web-oriented “super agent” example that wires browser automation, command execution, and file/code tools into one runnable assistant (`examples/components/web/super_agent/...`).

## 2. Agent Framework & Architecture

The actual runtime framework is **LangGraph + LangChain Core**, with custom orchestration abstractions (`Crew`, `Agent`, `Task`) layered on top. This is confirmed by imports such as `StateGraph`, `create_react_agent`, and `Command` in `libs/langcrew/langcrew/crew.py:14-20`, `libs/langcrew/langcrew/executors/react_executor.py:12-14`, plus LangChain message/tool primitives in `libs/langcrew/langcrew/agent.py:8-11`. It is **not CrewAI runtime internals**; it provides CrewAI-compatible surface methods (`kickoff`) but executes through LangGraph (`libs/langcrew/langcrew/crew.py:1305-1388`).

Architecture-wise, each `Task` delegates to an `Agent`, and each `Agent` builds/caches an executor (default `react`) that wraps LangGraph’s prebuilt ReAct loop (`libs/langcrew/langcrew/task.py:204-210`, `libs/langcrew/langcrew/agent.py:349-430`, `libs/langcrew/langcrew/executors/react_executor.py:79-112`). Prompt “intelligence” primarily lives in agent role/goal/backstory templating (`PromptBuilder`) or custom prompt injection (`libs/langcrew/langcrew/agent.py:383-399`, `468-510`). Workflow intelligence lives in `Crew`, which chooses one of several graph construction modes: sequential tasks, sequential agents, agent handoff graph, or task handoff graph with router (`libs/langcrew/langcrew/crew.py:970-1001`).

## 3. Orchestration Pattern

Closest match: **Graph orchestration (LangGraph state machine), with optional sequential and handoff-based manager/router behavior**.

Control flow is explicitly built as a `StateGraph` and compiled; mode selection is dynamic:

```470:498:libs/langcrew/langcrew/crew.py
def _build_task_sequential_graph(...):
    builder = StateGraph(CrewState)
    prev_node = START
    ...
    for i, task in enumerate(self.tasks):
        node_name = self._get_task_node_name(task, i)
        builder.add_node(node_name, create_task_node(task))
        builder.add_edge(prev_node, node_name)
        prev_node = node_name
    builder.add_edge(prev_node, END)
```

And routing/handoff behavior uses LangGraph `Command(goto=...)`:

```938:954:libs/langcrew/langcrew/crew.py
if backbone_execution_state["current_index"] < len(backbone_tasks):
    current_task = backbone_tasks[backbone_execution_state["current_index"]]
    task_name = get_task_identifier(current_task)
    backbone_execution_state["current_index"] += 1
    return Command(goto=task_name)

return Command(goto=END)
```

So it is not a peer swarm; it is graph-compiled workflow execution with explicit routing edges and command-based jumps.

## 4. Tools & External Integrations

- **MCP servers/tools**: agents can auto-load MCP tools via `MultiServerMCPClient` (`libs/langcrew/langcrew/tools/mcp.py:14, 26-64`), configured at agent level (`libs/langcrew/langcrew/agent.py:46-47, 235-287`).  
- **LLM providers**: OpenAI, Anthropic, Bedrock, DeepSeek, Vertex, OpenAI-compatible endpoints via LangChain adapters (`libs/langcrew/langcrew/llm_factory.py:26-203`).  
- **Browser automation**: `BrowserStreamingTool` wraps `browser-use` agent/session/controller and streams intermediate events (`libs/langcrew-tools/langcrew_tools/browser/browser_use_streaming_tool.py:22-24, 96-111, 568-615`).  
- **Terminal/shell execution**: `RunCommandTool` executes commands in sandbox (`cd /workspace && ...`) and supports background handles (`libs/langcrew-tools/langcrew_tools/commands/langchain_tools.py:35-71`).  
- **Web search/fetch services**: `WebSearchTool` calls external retriever endpoint via HTTP (`libs/langcrew-tools/langcrew_tools/search/langchain_tools.py:25-33, 104-135`); `WebFetchTool` calls crawl4ai HTTP service (`libs/langcrew-tools/langcrew_tools/fetch/langchain_tools.py:29-49, 239-288`).  
- **Memory and persistence backends**: LangGraph checkpointer/store providers include memory, Postgres, Redis, MongoDB, MySQL, SQLite (`libs/langcrew/langcrew/memory/factory.py:10-124, 127-249`).  
- **Example tool wiring**: the “super agent” example combines browser/search/fetch/filesystem/image/code interpreter/run-command tools in one agent (`examples/components/web/super_agent/src/super_agent/agent/crew.py:156-175`).

## 5. Notable Code Walkthrough

- `libs/langcrew/langcrew/crew.py:470-1001` - Core orchestration engine that compiles different execution graphs (sequential tasks/agents, agent handoff, task handoff with router) and dispatches execution/streaming through LangGraph.
- `libs/langcrew/langcrew/agent.py:349-430` - Agent runtime where per-task executors are built, prompts are selected (custom or CrewAI-style), and tools/hooks/interrupts are injected into executor creation.
- `libs/langcrew/langcrew/executors/react_executor.py:79-112` - ReAct executor implementation using `create_react_agent`, which is where tool-calling LLM loops actually run.
- `libs/langcrew-tools/langcrew_tools/browser/browser_use_streaming_tool.py:328-347, 568-615` - Browser-use integration that initializes browser agent sessions and emits structured streaming events for UI/control.
- `examples/components/web/super_agent/src/super_agent/agent/crew.py:156-204` - Concrete production-style assembly of one powerful agent plus tool stack, run through `RunnableCrew` for session-aware streaming and interruption.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only **partially** accurate. The repository’s core is a **general multi-agent workflow framework**; browser and terminal capabilities are optional tools, not the main runtime abstraction (`libs/langcrew/langcrew/crew.py`, `agent.py`). In the super-agent example, browser automation (`BrowserStreamingTool`) and terminal commands (`RunCommandTool`) are clearly realized (`examples/components/web/super_agent/src/super_agent/agent/crew.py:159-175`), so browser/terminal is supported. But across the whole repo, the dominant pattern is orchestrating multi-step LLM task pipelines, so **Workflow Automation** is the better primary category.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear LangGraph-based orchestration with multiple execution modes (sequential + handoff/router graphs).
  - Strong integration surface: MCP, many LLM backends, memory stores, browser/command/file/code tools.
  - Practical runtime features for production apps: streaming events, session IDs, interrupt-before/after, HITL hooks.
  - Good separation of concerns (`Crew` orchestration vs `Agent` execution vs `Task` context/output handling).
  - Includes realistic examples (web super-agent, MCP integration) beyond toy demos.

- **Limitations:**
  - Some tool integrations rely on external infra/env setup (search endpoint, crawl4ai, sandbox, API keys), so out-of-box reproducibility is limited.
  - Multi-agent coordination is mostly deterministic graph routing; little adaptive planning/negotiation among peer agents.
  - Certain features are concentrated in examples rather than universally enabled defaults (e.g., browser/terminal stack).
  - Complexity in handoff/router logic may be hard to verify formally without stronger integration tests for all graph modes.
  - Mixed abstraction style (CrewAI compatibility + native LangGraph) can increase conceptual overhead.

- **Research relevance:**
  - Evidence of an applied **graph-based MAS orchestration** design in modern LLM systems.
  - Useful case study for **tool-augmented agent workflows** (MCP + browser + shell + memory).
  - Demonstrates practical **human-in-the-loop interruption and resume patterns** in agent runtimes.
  - Illustrates how CrewAI-style role/task semantics can be mapped onto LangGraph execution primitives.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
