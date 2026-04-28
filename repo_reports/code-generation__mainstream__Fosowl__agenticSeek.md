---
repo_name: Fosowl/agenticSeek
url: "https://github.com/Fosowl/agenticSeek"
stars: 26045
forks: 2916
contributors_count: 41
last_commit_date: "2026-04-22T07:42:23+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, Browser / Terminal Use]
generated_at: "2026-04-27T10:36:22.130650+00:00"
model: auto
duration_s: 66.9
clone_size_kb: 18659
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`agenticSeek` is a local-first autonomous assistant that users run via CLI (`python cli.py`) or API server (`python api.py`) to execute mixed tasks such as coding, file operations, and web browsing. At runtime it instantiates multiple specialized LLM agents (casual/chat, coder, file, browser, plus a planner for complex tasks), then routes each user request to one agent or to a planner that delegates subtasks. The system couples LLM outputs with executable tool blocks (e.g., code fences tagged `python`, `bash`, `web_search`) and iterates on tool feedback until completion. In practice, users get a task-performing assistant that can generate code, run it, search/navigate the web, and manipulate local files within a defined work directory.

## 2. Agent Framework & Architecture

This repository does **not** use CrewAI, LangGraph, LangChain, AutoGen, or LlamaIndex as its core runtime framework. The orchestration is a **custom multi-agent architecture** implemented directly in project code (`sources/interaction.py`, `sources/router.py`, `sources/agents/*.py`), with custom tool execution abstractions in `sources/tools/tools.py`. The dependency list confirms no CrewAI/LangGraph runtime imports in core paths (`requirements.txt`, `pyproject.toml`).

The architecture is role-based: `CasualAgent`, `CoderAgent`, `FileAgent`, `BrowserAgent`, and `PlannerAgent` are created in entrypoints (`cli.py:36-55`, `api.py:104-130`). `Interaction.think()` performs top-level control: route query -> call selected agent -> return answer (`sources/interaction.py:149-169`). Routing intelligence lives in `AgentRouter`, which combines a zero-shot BART classifier with an `AdaptiveClassifier` plus a complexity estimator; high-complexity queries are forced to planner (`sources/router.py:401-461`).

The planner is itself an LLM-driven manager: it asks the model for a JSON plan, validates tasks, executes subtasks on internal worker agents (`coder/file/web/casual`), and can re-plan after each step based on success/failure (`sources/agents/planner_agent.py:150-303`). Prompt files in `prompts/base/*.txt` and `prompts/jarvis/*.txt` hold much of behavior policy.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with dynamic routing**.

At the top level, a router chooses either a specialist worker directly or the planner for complex requests:

```452:460:sources/router.py
lang = self.lang_analysis.detect_language(text)
text = self.find_first_sentence(text)
text = self.lang_analysis.translate(text, lang)
labels = [agent.role for agent in self.agents]
complexity = self.estimate_complexity(text)
if complexity == "HIGH":
    pretty_print(f"Complex task detected, routing to planner agent.", color="info")
    return self.find_planner_agent()
```

Inside planner mode, the planner generates a plan and dispatches tasks to worker agents sequentially, then optionally updates the remaining plan:

```275:301:sources/agents/planner_agent.py
self.status_message = "Making a plan..."
agents_tasks = await self.make_plan(goal)
...
while i < steps and not self.stop:
    task_name, task = agents_tasks[i][0], agents_tasks[i][1]
    ...
    answer, success = await self.start_agent_process(task, required_infos)
    agents_work_result[task['id']] = answer
    agents_tasks = await self.update_plan(goal, agents_tasks, agents_work_result, task['id'], success)
    steps = len(agents_tasks)
    i += 1
```

So control flow is manager-worker, not graph-state-machine or peer swarm.

## 4. Tools & External Integrations

- **LLM providers (local + cloud)**: Unified provider layer supports Ollama, OpenAI-compatible backends, Anthropic, Together, Google, OpenRouter, MiniMax, DeepSeek, and local server endpoints (`sources/llm_provider.py:27-41`, `:123-498`).
- **Local/remote browser automation (Selenium + undetected-chromedriver)**: Browser is created and injected into `BrowserAgent`; supports navigation, text extraction, links/forms, screenshotting, anti-detection options (`sources/browser.py:259-284`, `:285-822`; wired in `cli.py:31-34`, `api.py:98-101`).
- **Web search via self-hosted SearxNG**: `BrowserAgent` uses `searxSearch` tool, which posts to `SEARXNG_BASE_URL/search` and parses results (`sources/agents/browser_agent.py:28-30`, `:350-355`; `sources/tools/searxSearch.py:12-27`, `:62-107`).
- **Code execution toolchain**: `CoderAgent` executes fenced blocks with Bash, Python, C, Go, Java interpreters and loops on execution feedback (`sources/agents/code_agent.py:21-28`, `:64-83`; generic block parser/executor in `sources/agents/agent.py:255-285`, `sources/tools/tools.py:154-205`).
- **Filesystem operations**: `FileAgent` uses `FileFinder` and Bash tools for local file tasks (`sources/agents/file_agent.py:15-18`).
- **MCP registry lookup (partial/WIP)**: `McpAgent` and `MCP_finder` exist for Smithery registry discovery but are marked under development and commented out in main agent list (`sources/agents/mcp_agent.py:9-23`, `cli.py:52-55`, `sources/tools/mcpFinder.py:11-67`).
- **API/backend services**: FastAPI endpoints for query processing and status (`api.py:48-289`), Celery configured with Redis (`api.py:46-50`), frontend served separately.

## 5. Notable Code Walkthrough

- `sources/interaction.py:149-169` - Central runtime loop for one user turn: routes query, invokes chosen agent asynchronously, tracks current agent/output, and manages memory handoff.
- `sources/router.py:441-471` - Multi-stage routing logic (language normalization, complexity estimation, hybrid classifier vote) that determines whether to invoke planner vs direct specialist.
- `sources/agents/planner_agent.py:150-303` - Core multi-agent manager: generates JSON plan, delegates tasks to worker agents, aggregates outputs, and replans on failures.
- `sources/agents/code_agent.py:46-87` - Representative tool-using worker: prompts LLM, detects executable blocks, runs interpreters, and retries with corrective loop.
- `sources/agents/browser_agent.py:331-435` - Autonomous browser workflow: search query synthesis, SERP selection, iterative navigation/form handling, note-taking, and final synthesis answer.

## 6. Use-Case Mapping

The repo does support **Code Generation** (via `CoderAgent` with multi-language execution and iterative correction), but the implemented system is broader: it routes across coding, web research/navigation, and filesystem tasks, and for complex goals uses planner-driven decomposition across heterogeneous agents. In other words, code generation is one capability inside a larger autonomous task-execution pipeline (`sources/router.py:455-461`, `sources/agents/planner_agent.py:25-30`). Given actual runtime behavior, the better single label is **Workflow Automation** rather than pure Code Generation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Explicit multi-agent runtime with planner-worker decomposition, not just prompt-role simulation (`sources/agents/planner_agent.py`).
  - Practical hybrid routing (zero-shot + adaptive classifier + complexity gating) for task triage (`sources/router.py:370-390`, `:401-461`).
  - Tight tool-feedback loop where execution outcomes directly steer next LLM steps (`sources/agents/agent.py:266-285`).
  - Broad local-operational scope: browser automation, code execution, file operations, local LLM support (`sources/browser.py`, `sources/agents/code_agent.py`).
  - Supports both interactive CLI and API service deployment (`cli.py`, `api.py`).

- **Limitations:**
  - Planner protocol is brittle: relies on strict JSON-in-markdown parsing; retries but can still fail often with weaker models (`sources/agents/planner_agent.py:150-179`).
  - Task dependencies appear unsafe when `need` is missing/null; planner loop assumes `task['need']` exists (`sources/agents/planner_agent.py:290-292`).
  - Browser loop has many heuristic branches and may cycle/stall despite anti-stuck prompt logic (`sources/agents/browser_agent.py:357-409`).
  - Security/sandboxing for code execution is limited; interpreters and bash run in host work directory by design.
  - MCP integration is incomplete and disabled by default in main initialization (`cli.py:52-55`, `sources/agents/mcp_agent.py:9`).

- **Research relevance:**
  - Useful evidence for **lightweight hierarchical MAS** implemented without heavyweight orchestration frameworks.
  - Demonstrates **tool-grounded autonomous loops** where environment feedback (execution/web state) is fed back into planning.
  - Illustrates a hybrid of **learned routing + planner fallback** as a practical architecture for mixed-task assistants.
  - Provides an example of local-first agent engineering tradeoffs (capability breadth vs reliability/safety guarantees).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
