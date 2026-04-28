---
repo_name: dnhkng/GLaDOS
url: "https://github.com/dnhkng/GLaDOS"
stars: 5515
forks: 428
contributors_count: 31
last_commit_date: "2026-04-09T06:25:12+00:00"
primary_use_case: Workflow Automation
user_tier: Mainstream
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T12:10:53.410312+00:00"
model: auto
duration_s: 72.5
clone_size_kb: 37986
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`dnhkng/GLaDOS` is a local-first voice assistant that combines ASR, LLM reasoning, tool calling, and TTS into a continuously running runtime (`glados start` / `glados tui`). In addition to normal user-driven chat, it can run autonomous background loops that monitor context (time, vision changes, task slots) and decide whether to act. Users get a conversational assistant persona (GLaDOS-style) that can speak, use built-in/MCP tools, and surface background updates like weather/news. With autonomy jobs enabled, it behaves more like an always-on orchestration system than a single request/response bot.

## 2. Agent Framework & Architecture

This repo uses a **custom multi-agent architecture**, not LangGraph/CrewAI/AutoGen/LangChain orchestration. Evidence: custom base classes and manager in `src/glados/autonomy/subagent.py:63-278` and `src/glados/autonomy/subagent_manager.py:33-220`, plus direct `requests/httpx` LLM calls in `src/glados/core/llm_processor.py:695-745` and `src/glados/autonomy/llm_client.py:34-88`.

High-level design: a main conversational agent runs through `LanguageModelProcessor` + `ToolExecutor`, while multiple background “minds” (subagents) run in independent threads and write to a shared slot store. `Glados` wires these components and registers built-in subagents (emotion, compaction, observer, optional weather/news) in `src/glados/core/engine.py:635-760`. The main agent consumes slot summaries as injected system context (`[tasks]`) and can react through autonomy prompts (`src/glados/autonomy/loop.py:121-159`).

The “intelligence” lives in several places: (1) primary chat model + function/tool calling (`llm_processor`), (2) autonomy prompt templates in config (`src/glados/autonomy/config.py:120-139`), and (3) specialized LLM-based decision logic inside subagents (e.g., observer/emotion/weather/news agents).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker with event-driven triggers** (hybrid).  
- Manager layer: `Glados` + `SubagentManager` creates/starts multiple worker agents (`engine.py:303-309`, `subagent_manager.py:115-125`).  
- Worker layer: each subagent ticks on its own cadence and writes to shared slots (`subagent.py:221-253`).  
- Event-driven bridge: `AutonomyLoop` listens to tick/vision/task events and dispatches autonomous LLM prompts (`loop.py:63-88`).

Control flow excerpt 1 (`src/glados/core/engine.py:631-639`, `649-658`):
```python
# Start subagents after other components are running
if self.subagent_manager:
    self.subagent_manager.start_all()

if jobs_config.hacker_news.enabled:
    hn_subagent = HackerNewsSubagent(...)
    self.subagent_manager.register(hn_subagent)
```

Control flow excerpt 2 (`src/glados/autonomy/subagent.py:221-229`, `src/glados/autonomy/loop.py:147-157`):
```python
self.write_slot(
    status=output.status,
    summary=output.summary,
    report=output.report,
    notify_user=output.notify_user,
)

return self._config.tick_prompt.format(
    now=now, since_user=since_user_text, scene=scene or "unknown", tasks=tasks
)
```

## 4. Tools & External Integrations

- **LLM API endpoints (OpenAI-style or Ollama-compatible)**: streaming chat completion calls in `src/glados/core/llm_processor.py:717-732`; simple JSON calls in `src/glados/autonomy/llm_client.py:50-67` and `src/glados/core/llm_decision.py:96-111`.
- **Built-in function tools** (`speak`, `do_nothing`, `get_report`, `vision_look`, preferences, slow clap): registered in `src/glados/tools/__init__.py:15-37`, executed by `src/glados/core/tool_executor.py:176-185`.
- **MCP servers/tools/resources**: dynamic MCP tool discovery + invocation in `src/glados/mcp/manager.py:97-102`, `126-143`, then merged into tool list in `src/glados/core/llm_processor.py:616-621`.
- **External HTTP data sources for subagents**:
  - Hacker News API in `src/glados/autonomy/agents/hacker_news.py:122-127`, `145-150`.
  - Open-Meteo weather API in `src/glados/autonomy/agents/weather.py:226-233`.
- **Local memory/filesystem persistence**: preferences/knowledge stores in `src/glados/core/engine.py:268-272`; long-term facts written by compaction agent via memory server in `src/glados/autonomy/agents/compaction_agent.py:170-179`.
- **Audio/voice stack** (ASR/TTS) is core but not an “agent tool”; wired in engine orchestration (`src/glados/core/engine.py:366-398`, `469-489`).

## 5. Notable Code Walkthrough

- `src/glados/core/engine.py:166-760` - central orchestrator that initializes queues, LLM lanes, tool executor, autonomy loop, MCP manager, and subagent registration; this is where multi-agent runtime composition actually happens.
- `src/glados/core/llm_processor.py:556-621, 685-703, 746-778` - builds context/tool payloads, streams LLM output, aggregates tool calls, and routes tool executions; core “reasoning + act” loop for the main agent.
- `src/glados/autonomy/subagent.py:63-169, 221-253` - abstract subagent contract and threaded tick loop; defines how each background agent produces structured outputs into shared slots.
- `src/glados/autonomy/loop.py:63-88, 121-159` - event consumer that converts time/vision/task updates into autonomous prompts and enqueues them on the autonomy lane.
- `src/glados/mcp/manager.py:51-102, 126-143, 253-281` - MCP integration layer providing dynamic external tools/resources, effectively extending agent action space at runtime.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. This code automates recurring workflows (periodic monitoring, context compaction, behavior self-regulation, weather/news polling, event-triggered autonomy decisions) through coordinated agents and shared task slots rather than manual user prompting every step. The system continuously orchestrates background jobs, tool invocations, and prioritization between user lane vs autonomy lane (`src/glados/core/engine.py:395-446`, `src/glados/autonomy/loop.py:77-87`, `src/glados/autonomy/agents/*.py`). It is also a voice assistant, but the distinctive agentic behavior is long-running workflow orchestration.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Real runtime multi-agent coordination (manager + multiple specialized subagents) rather than “role-play agents.”
  - Clear separation of priority vs autonomy inference lanes for responsiveness under background load (`engine.py:395-446`).
  - Unified tool-calling path that supports both built-in tools and dynamic MCP tools (`llm_processor.py:604-621`, `mcp/manager.py:97-102`).
  - Practical shared-memory primitive via slots, with importance/confidence metadata (`autonomy/slots.py:30-113`).
  - Includes self-maintenance agents (compaction/observer/emotion), not just external data fetchers.

- **Limitations:**
  - Heavy thread/queue architecture increases race-condition and state-consistency risk; limited formal state-machine guarantees.
  - Subagent LLM calls are mostly ad hoc prompt+JSON parsing (less robust than strict tool schemas/typed planners).
  - No advanced planning graph or explicit inter-agent negotiation protocol; coordination is mostly slot-mediated and centralized.
  - External integrations are mostly polling APIs + MCP; no deeper transactional workflow engine or retry orchestration semantics.
  - Default autonomy/jobs are disabled in config, so MAS features are opt-in (`configs/glados_config.yaml:16-38`).

- **Research relevance:**
  - Good evidence for **pragmatic MAS in production-like assistant systems** (hybrid reactive + autonomous loops).
  - Useful case of **shared blackboard/slot communication** between specialized agents and a primary dialog agent.
  - Demonstrates **tool-augmented autonomy with lane prioritization** as a systems design pattern.
  - Relevant for studies on **personality/stateful meta-agents** (observer/emotion) influencing primary agent behavior.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
