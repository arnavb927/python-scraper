---
repo_name: 666ghj/MiroFish
url: "https://github.com/666ghj/MiroFish"
stars: 56913
forks: 8749
contributors_count: 3
last_commit_date: "2026-04-02T08:52:29+00:00"
primary_use_case: Simulation
user_tier: Niche
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Simulation]
generated_at: "2026-04-27T10:15:09.182708+00:00"
model: auto
duration_s: 67.6
clone_size_kb: 15560
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`MiroFish` is a Flask + Vue system that prepares and runs social-media simulations where many LLM-driven agents act on Twitter- and Reddit-like environments, seeded from a Zep knowledge graph. A user typically creates a project, builds/loads a graph, calls simulation preparation APIs, then starts a run (`/api/simulation/start`) that launches backend scripts to execute rounds of agent actions and logs them. The platform generates agent profiles and simulation parameters with LLMs, executes the simulation through OASIS/CAMEL environments, and streams action timelines/interview results back to the UI. In practice, users get a controllable “what-if” behavioral forecast of how different entities might react under a scenario.

## 2. Agent Framework & Architecture

Framework usage is **not CrewAI/LangGraph**. The runtime imports and uses `oasis` + `camel-ai` (`generate_twitter_agent_graph`, `generate_reddit_agent_graph`, `LLMAction`, `ManualAction`) in `backend/scripts/run_parallel_simulation.py:160-170,1101-1160,1293-1351`. LLM calls for config/profile/report generation use OpenAI-compatible APIs via `openai` SDK wrappers (`backend/app/utils/llm_client.py:9-68`, `backend/app/services/simulation_config_generator.py:19-25,238-241`).

Architecture has two layers: (1) **preparation layer** that reads graph entities, generates agent personas, and creates simulation configs (`backend/app/services/simulation_manager.py:230-447`), and (2) **execution layer** that instantiates multi-agent environments for Twitter/Reddit and steps active agents each round (`backend/scripts/run_parallel_simulation.py:1228-1276,1427-1475`). The “intelligence” is distributed across prompt-heavy generators (profiles/config/report) plus OASIS agent policies invoked through `LLMAction`.

A third layer supports **post-run interaction**: the environment can stay alive and accept IPC interview commands, allowing direct questioning of specific agents or batches (`backend/scripts/run_parallel_simulation.py:217-299,345-415,560-601,1595-1634`; API wiring in `backend/app/api/simulation.py:2142-2490`).

## 3. Orchestration Pattern

Closest match: **swarm (peer multi-agent) with scheduled/event-driven activation**.

Why:
- Per round, a subset of agents is selected probabilistically by activity profiles/hours, then each selected agent acts in parallel with `LLMAction` (no central planner assigning per-task decomposition) (`backend/scripts/run_parallel_simulation.py:1040-1090,1239-1255,1438-1454`).
- Two platform worlds can run concurrently via `asyncio.gather(...)`, effectively two swarms in parallel (`backend/scripts/run_parallel_simulation.py:1584-1589`).

Control flow excerpt (selection + stepping):
- `active_agents = get_active_agents_for_round(...)`
- `actions = {agent: LLMAction() for _, agent in active_agents}`
- `await result.env.step(actions)`  
  (`backend/scripts/run_parallel_simulation.py:1239-1255`)

Control flow excerpt (dual-platform orchestration):
- `results = await asyncio.gather(run_twitter_simulation(...), run_reddit_simulation(...))`  
  (`backend/scripts/run_parallel_simulation.py:1584-1589`)

## 4. Tools & External Integrations

- **OASIS simulation engine + CAMEL model abstraction**: core multi-agent environment and action execution (`backend/scripts/run_parallel_simulation.py:160-170,1138-1160,1329-1351`).
- **OpenAI-compatible LLM endpoints**: used for persona generation, simulation config generation, and report generation (`backend/app/utils/llm_client.py:30-68`; `backend/app/services/oasis_profile_generator.py:196-199,530-539`; `backend/app/services/simulation_config_generator.py:238-241,443-452`).
- **Zep Cloud graph APIs**: read entities/context and optionally write back simulated activities as graph memory (`backend/app/services/oasis_profile_generator.py:19,327-333`; `backend/app/services/zep_graph_memory_updater.py:15,414-418`; enabled in runner at `backend/app/services/simulation_runner.py:372-385,682-685`).
- **SQLite local DBs**: each platform writes simulation traces, then code mines `trace/post/comment/user` tables for actions/context (`backend/scripts/run_parallel_simulation.py:657-747,857-981`).
- **IPC via filesystem command/response folders**: interview and environment control in persistent mode (`backend/scripts/run_parallel_simulation.py:205-215,238-299,560-601`).
- **Flask API + frontend integration**: orchestration endpoints for prepare/start/status/interview/history (`backend/app/api/simulation.py:359-639,1451-1642,2142-2573`).

No browser automation, shell-agent tooling, MCP servers, or vector DB like Pinecone/Chroma found in core MAS runtime.

## 5. Notable Code Walkthrough

- `backend/scripts/run_parallel_simulation.py:1101-1490` - Core MAS runtime: builds agent graphs for two platforms, runs round loops, schedules active agents, executes `LLMAction`, logs resulting actions from DB traces.
- `backend/app/services/simulation_manager.py:230-447` - End-to-end preparation pipeline: graph entity filtering, profile generation, and LLM-driven config generation before simulation can run.
- `backend/app/services/simulation_config_generator.py:243-379,813-907` - Multi-step config intelligence: time/event generation + batched per-agent behavior parameters (activity, stance, response delay, influence).
- `backend/app/services/oasis_profile_generator.py:212-275,497-581,851-1015` - Builds detailed personas per entity (LLM or fallback rules), including Zep-enriched context and concurrent profile generation.
- `backend/app/services/simulation_runner.py:313-479,482-553,1428-1608` - Process-level orchestration and monitoring around simulation scripts, including run-state persistence and interview API bridge.
- `backend/app/services/report_agent.py:865-955,1221-1531` - Separate ReACT-style report-writing agent with tool calls over simulation graph context; agentic but downstream from core simulation run.

## 6. Use-Case Mapping

The assigned label **Simulation** is accurate for the repository’s primary runtime behavior. The main product behavior is constructing many social agents, stepping them through simulated time, and observing emergent interactions under configurable scenarios (`backend/scripts/run_parallel_simulation.py:1214-1289,1412-1488`).  

That said, there is substantial **Workflow Automation** around simulation prep/execution/reporting APIs (`backend/app/api/simulation.py`), so the project sits at Simulation + workflow orchestration; but the core MAS contribution is simulation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Implements true runtime multi-agent environments (not just “agent” branding) with coordinated concurrent actions across many agents.
  - Supports dual-world parallel simulation (Twitter + Reddit) with unified configuration and logging.
  - Rich preparation pipeline links knowledge graph entities to personas and behavior parameters.
  - Keeps environment alive for post-hoc in-simulation interviews, enabling deeper qualitative analysis.
  - Strong operational plumbing: persistent run state, process control, replayable action logs, and optional graph-memory writeback.

- **Limitations:**
  - Heavy dependence on external LLM quality and prompt reliability; little formal guardrail/verification of generated configs/personas.
  - Coordination policy is mostly stochastic per-agent activation; limited explicit strategic planning or negotiation protocols among agents.
  - Significant complexity in scripts and service classes; maintainability/testing burden appears high.
  - No obvious benchmark harness for reproducibility across seeds/models in code paths reviewed.
  - Some components (report agent) are prompt-fragile and regex-parse tool-calls rather than using stricter function-calling protocols.

- **Research relevance:**
  - Evidence of practical **large-scale social MAS simulation** using LLM agents in platform-like environments.
  - Useful case study in **hybrid architecture**: deterministic orchestration + probabilistic agent behavior + LLM-generated parameterization.
  - Demonstrates **post-simulation agent interrogation** (interviews) as an analysis method for emergent behavior studies.
  - Shows an applied pattern for **graph-grounded scenario setup** feeding multi-agent simulation.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
