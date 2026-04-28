---
repo_name: LeapLabTHU/cooragent
url: "https://github.com/LeapLabTHU/cooragent"
stars: 1753
forks: 149
contributors_count: 12
last_commit_date: "2026-03-25T03:02:02+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T14:21:42.828834+00:00"
model: auto
duration_s: 79.7
clone_size_kb: 10108
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`cooragent` is a Python CLI/server system for building and running collaborative LLM workflows where multiple role-specific agents (e.g., coordinator, planner, publisher, coder, researcher/browser, reporter) execute a user task in sequence. A user typically runs `python cli.py` and then commands like `run-l` (launch), `run-o` (polish), or `run-p` (production) to generate, refine, and replay workflows (`cli.py:452-505`, `cli.py:1042-1050`, `cli.py:658-666`). At runtime, the system routes the request through planning and delegation nodes, then executes selected worker agents with tools via ReAct-style tool calling (`src/workflow/coor_task.py:78-190`). It also supports creating new agents on the fly through an `agent_factory` node (`src/workflow/coor_task.py:25-75`). The output is an event stream of agent steps/messages and final workflow completion, optionally persisted in workflow cache (`src/workflow/process.py:168-278`).

## 2. Agent Framework & Architecture

This repo is **not CrewAI** in core execution. It is a **custom multi-agent orchestrator** implemented on top of **LangGraph/LangChain primitives**: `Command` from `langgraph.types`, `MessagesState` state model, and `create_react_agent` from `langgraph.prebuilt` (`src/workflow/coor_task.py:4`, `src/interface/agent.py:140-152`, `src/workflow/coor_task.py:14`, `src/workflow/dynamic.py:53-57`). LLM backends are OpenAI-compatible (`ChatOpenAI`) plus DeepSeek wrappers (`src/llm/llm.py:1-3`, `src/llm/llm.py:70-105`).

Architecture is a layered manager-worker design. `AgentManager` loads default/user agents and tool registry (`src/manager/agents.py:54-103`, `src/manager/agents.py:185-231`). A workflow state carries team members, messages, next node, plan, and mode (`src/interface/agent.py:140-152`). The “intelligence” is split between prompt templates (`src/prompts/*.md`) and node logic in `coor_task.py`:  
- `coordinator` decides whether to hand off to planner;  
- `planner` produces JSON steps;  
- `publisher` picks next agent from steps;  
- `agent_proxy` executes chosen agent with tools (`src/workflow/coor_task.py:280-318`).

There is also a dynamic workflow builder (`src/workflow/dynamic.py`) that can instantiate execution nodes from JSON graph definitions and optionally inject MCP tools per run (`src/workflow/dynamic.py:33-93`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with state-machine-like control nodes**.

Control flow is centralized by system nodes (`coordinator -> planner -> publisher -> agent_proxy`) rather than peer-to-peer swarm behavior. `publisher` acts as dispatcher and `agent_proxy` runs the chosen worker, then returns to `publisher` for the next step (`src/workflow/coor_task.py:78-139`, `src/workflow/coor_task.py:142-189`).

```153:189:src/workflow/coor_task.py
agent = create_react_agent(
    get_llm_by_type(_agent.llm_type),
    tools=[
        agent_manager.available_tools[tool.name] for tool in _agent.selected_tools
    ],
    prompt=apply_prompt(state, _agent.prompt),
)
response = await agent.ainvoke(state, config=config)
...
return Command(
    update={...},
    goto="publisher",
)
```

```84:109:src/workflow/coor_task.py
if state["workflow_mode"] == "launch":
    ...
    response = await (
        get_llm_by_type(AGENT_LLM_MAP["publisher"])
        .with_structured_output(Router)
        .ainvoke(messages)
    )
    agent = response["next"]
    if agent == "FINISH":
        goto = "__end__"
    elif agent != "agent_factory":
        goto = "agent_proxy"
    else:
        goto = "agent_factory"
```

## 4. Tools & External Integrations

- **Web search (Tavily)** via `TavilySearchResults`, wrapped to inject current time into queries (`src/tools/search.py:5-17`, `src/tools/search.py:95-97`), registered in tool manager (`src/manager/agents.py:91-98`).
- **Web crawling/content extraction** via custom `Crawler` (`src/tools/crawl.py:13-23`, `src/tools/crawler/crawler.py`), also registered in manager (`src/manager/agents.py:95`).
- **Shell/terminal execution** via `bash_tool` (`subprocess.run(..., shell=True)`) (`src/tools/bash_tool.py:22-41`), registered in manager (`src/manager/agents.py:93`).
- **Python execution** via `python_repl_tool` import/registration (`src/manager/agents.py:16`, `src/manager/agents.py:96`).
- **Browser-use style browsing through external backend API**: `browser_tool` calls `GET {BROWSER_BACKEND}/scroll` and LLM-summarizes HTML (`src/tools/browser.py:93-117`, `src/tools/browser.py:140-153`), with enable flag `USE_BROWSER` (`src/tools/browser.py:28-31`, `src/manager/agents.py:99-100`).
- **MCP servers/tools** using `MultiServerMCPClient` and `config/mcp.json` parsing (`src/manager/mcp.py:11-76`, `src/manager/agents.py:85-90`, `src/workflow/dynamic.py:49-53`).
- **FastAPI/SSE-facing service layer** exists (`fastapi`, `sse-starlette` in deps; server wrapper in `src/service/server.py:24-67`) but primary interaction shown is CLI.
- **No vector DB/RAG store wiring in core runtime** despite placeholders in config template (`config/workflow.json:44-49`).

## 5. Notable Code Walkthrough

- `src/workflow/coor_task.py:25-318` - Core orchestration nodes: agent creation, planning, dispatch, and worker execution. This is where multi-agent runtime behavior actually happens.
- `src/workflow/process.py:54-166` - Entry point for workflow runs; assembles state (team members/tools/user query), chooses graph (`build_graph` vs `agent_factory_graph`), and streams events.
- `src/manager/agents.py:54-103` - Central registry for available agents and tools, including conditional browser and MCP tool loading.
- `src/manager/agents.py:185-223` - Bootstraps default shared agents (`researcher`, `coder`, `browser`, `reporter`) with predefined tools/prompts.
- `src/prompts/publisher.md:5-25` - Prompt-level deterministic routing contract that forces publisher output to strict `{"next": ...}` JSON based on `steps`.
- `cli.py:452-505` - User-facing launch command that packages messages and starts streaming workflow execution to terminal.

## 6. Use-Case Mapping

Although it includes a browser tool and shell tool, the dominant runtime behavior is **workflow orchestration across multiple agents** (plan generation, task decomposition, sequential delegation, and execution tracking), not primarily autonomous browser/terminal control loops. Browser/terminal capabilities are used as subordinate tools of worker agents (`src/manager/agents.py:191-211`, `src/tools/bash_tool.py:17-45`, `src/tools/browser.py:93-153`). So the assigned label “Browser / Terminal Use” is partially true but secondary.

A better primary category is **Workflow Automation**: the system’s core value is generating and executing reusable multi-agent workflows across launch/polish/production modes (`README.md:25-35`, `src/workflow/coor_task.py:308-318`, `src/workflow/process.py:54-106`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-role separation (coordinator/planner/publisher/worker) with explicit control transfer via `Command.goto`.
  - Practical tool-grounded execution through ReAct agents and per-agent tool whitelists.
  - Supports runtime expansion by creating new agents (`agent_factory`) instead of fixed static teams.
  - Includes iterative lifecycle (launch/polish/production) and workflow persistence/cache for replay.
  - Integrates MCP for extensible external tool ecosystems.

- **Limitations:**
  - Custom graph engine (`src/workflow/graph.py`) is simplistic; edge metadata is mostly unused in the main async loop.
  - Some dynamic-path code quality issues (e.g., mixed sync/async patterns, broad `except`, potential undefined `env_value` path in MCP config) may affect robustness.
  - Heavy behavior dependence on prompt contracts rather than formal typed planners/executors.
  - Security risk surfaces from shell-enabled tool (`subprocess.run(..., shell=True)`), with limited visible sandboxing.
  - Incomplete polish-mode branches marked “support soon” suggest partial feature maturity.

- **Research relevance:**
  - Real-world example of hierarchical MAS orchestration with LLM-based planning and deterministic routing constraints.
  - Demonstrates agent-tool co-design: role prompts + constrained tool sets + dispatcher loop.
  - Shows practical pattern for “agent factory” (meta-agent that builds new task agents dynamically).
  - Useful evidence for studying workflow lifecycle management (build, refine, production replay) in agentic systems.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
