---
repo_name: nikmcfly/MiroFish-Offline
url: "https://github.com/nikmcfly/MiroFish-Offline"
stars: 2003
forks: 523
contributors_count: 6
last_commit_date: "2026-03-24T18:52:36+00:00"
primary_use_case: Simulation
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Simulation]
generated_at: "2026-04-27T12:43:45.707026+00:00"
model: auto
duration_s: 88.3
clone_size_kb: 17032
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`MiroFish-Offline` is a local-first social simulation system where users upload source text, build a knowledge graph, generate many LLM-driven agent personas, and then run a time-stepped Twitter/Reddit simulation. In practice, users call the Flask API flow (`/api/simulation/create` → `/prepare` → `/start`) or use the UI to do the same, and the backend launches OASIS simulation scripts that produce action logs and SQLite traces. The output is not just a chat response: it includes per-round agent actions, platform timelines, interviewable live agents, graph memory updates, and generated analytic reports. The core problem it solves is forecasting collective behavior under hypothetical scenarios by simulating many heterogeneous social actors rather than a single model response.

## 2. Agent Framework & Architecture

This repo does **not** use CrewAI/LangGraph/AutoGen as its runtime MAS framework. The actual multi-agent runtime is built on **OASIS + CAMEL-AI** (`camel-oasis`, `camel-ai`) with OpenAI-compatible model backends (`backend/requirements.txt:21-25`, `backend/scripts/run_parallel_simulation.py:161-170`, `backend/scripts/run_parallel_simulation.py:1034-1037`). Agent graphs are created through OASIS factory methods (`generate_twitter_agent_graph`, `generate_reddit_agent_graph`) and executed in OASIS environments (`oasis.make(...)`) in per-round loops (`backend/scripts/run_parallel_simulation.py:1138-1160`, `backend/scripts/run_parallel_simulation.py:1329-1351`, `backend/scripts/run_parallel_simulation.py:1228-1255`).

Architecture-wise, there are two layers of “intelligence.”  
1) **Simulation agents** (many) act inside OASIS environments each round via `LLMAction()` and occasional `ManualAction()` (e.g., interviews, seeded events).  
2) **Meta-agents/services** (single-agent style) prepare and analyze simulations using LLMs: profile generation (`oasis_profile_generator.py`), config synthesis (`simulation_config_generator.py`), and ReACT report generation (`report_agent.py`).  

The orchestration core is custom Python service code: `SimulationManager` prepares configs/profiles, `SimulationRunner` starts and monitors subprocess scripts, parses action logs, and exposes interview IPC (`backend/app/services/simulation_manager.py:229-450`, `backend/app/services/simulation_runner.py:312-520`).

## 3. Orchestration Pattern

Closest pattern: **hierarchical manager-worker**, with event/log-driven monitoring around it.

- **Manager-worker:** A central orchestrator (`SimulationRunner`) launches one or two platform workers (Twitter/Reddit scripts), while each worker drives many agents inside OASIS rounds.
- **Within each worker:** round-based sequential loop selects active agents, sends batched LLM actions, collects DB traces.

Control flow excerpt 1 (manager launching worker scripts):  
`backend/app/services/simulation_runner.py:389-398`, `backend/app/services/simulation_runner.py:440-450`
```python
if platform == "twitter":
    script_name = "run_twitter_simulation.py"
elif platform == "reddit":
    script_name = "run_reddit_simulation.py"
else:
    script_name = "run_parallel_simulation.py"

process = subprocess.Popen(
    cmd, cwd=sim_dir, stdout=main_log_file, stderr=subprocess.STDOUT, ...
)
```

Control flow excerpt 2 (worker executing many agent actions each round):  
`backend/scripts/run_parallel_simulation.py:1239-1255`
```python
active_agents = get_active_agents_for_round(result.env, config, simulated_hour, round_num)
if not active_agents:
    continue

actions = {agent: LLMAction() for _, agent in active_agents}
await result.env.step(actions)
```

So this is not a graph-state orchestrator (LangGraph-style), and not peer-to-peer swarm control among top-level agents; it is centrally scheduled simulation execution over many autonomous agent instances.

## 4. Tools & External Integrations

- **LLM API (OpenAI-compatible, often Ollama):** model calls for profiles/config/reporting via OpenAI SDK (`backend/app/utils/llm_client.py:33-86`, `backend/app/services/simulation_config_generator.py:237-251`, `backend/app/services/oasis_profile_generator.py:474-483`).
- **OASIS/CAMEL simulation runtime:** agent graph generation and environment stepping (`backend/scripts/run_parallel_simulation.py:161-170`, `backend/scripts/run_parallel_simulation.py:1138-1160`, `backend/scripts/run_parallel_simulation.py:1329-1351`).
- **Neo4j via GraphStorage:** graph retrieval and updates used by report tools and memory updater (`backend/app/services/graph_tools.py:396-437`, `backend/app/services/graph_memory_updater.py:323-329`).
- **SQLite simulation DBs:** action/interview traces read for logs and interview responses (`backend/scripts/run_parallel_simulation.py:687-692`, `backend/scripts/run_parallel_simulation.py:535-542`, `backend/app/services/simulation_runner.py:1677-1691`).
- **IPC filesystem command bus:** interview/close-env commands via `ipc_commands`/`ipc_responses` JSON files (`backend/scripts/run_parallel_simulation.py:205-215`, `backend/scripts/run_parallel_simulation.py:256-297`, `backend/scripts/run_parallel_simulation.py:560-601`).
- **Flask REST API + frontend integration:** operational control and monitoring endpoints (`backend/app/api/simulation.py:155-219`, `backend/app/api/simulation.py:1446-1622`, `backend/app/api/simulation.py:2137-2490`).
- **Local file artifacts:** simulation configs/profiles/actions/report files under uploads (`backend/app/services/simulation_manager.py:424-427`, `backend/scripts/action_logger.py` wiring via `run_parallel_simulation.py:158`).

No MCP server, browser automation, or terminal-use agent loop is implemented.

## 5. Notable Code Walkthrough

- `backend/scripts/run_parallel_simulation.py:1101-1290,1293-1490` - Core dual-platform simulation executor; creates agent graphs, runs per-round `LLMAction` batches, logs actions from SQLite traces, and supports post-run “wait mode” for interactive interviews.
- `backend/app/services/simulation_runner.py:312-520,582-689` - Process orchestrator and runtime monitor; starts script subprocesses, tails per-platform action logs, updates run state, and optionally streams activities into graph memory updater.
- `backend/app/services/simulation_config_generator.py:242-378,534-590,810-903` - LLM-driven parameter synthesis pipeline (time/event/agent configs), including batched generation and fallback rule logic when LLM output fails.
- `backend/app/services/oasis_profile_generator.py:204-267,441-525,795-954` - Generates rich agent personas from graph entities (LLM or rule-based), with optional graph retrieval enrichment and parallel profile generation.
- `backend/app/services/report_agent.py:866-915,1228-1509,1540-1747` - ReACT-style report-generation agent that repeatedly calls graph tools/interview tools and produces sectioned Markdown analysis.

## 6. Use-Case Mapping

The assigned label **Simulation** is correct for the primary runtime: the system simulates many social agents over time, with explicit rounds, activity schedules, action spaces, and platform dynamics (`run_parallel_simulation.py`). It does include substantial workflow automation (prepare/start/monitor/report APIs), but that automation is in service of the simulation loop rather than being the end goal. So the dominant realized use case in code is simulation of social/public-opinion dynamics using coordinated LLM agents.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Real multi-agent runtime with many concurrent role-conditioned agents, not just prompt-role emulation.
  - End-to-end pipeline from document → graph → personas → simulation → interviews → report in one codebase.
  - Practical observability: action logs, run states, timeline stats, interview history, and per-platform separation.
  - Strong local-stack portability (OpenAI-compatible LLM endpoint + Neo4j + filesystem IPC).
  - Hybrid retrieval + interview tooling gives richer post-simulation analysis than pure log summarization.

- **Limitations:**
  - Heavy behavior logic depends on external OASIS internals; core agent cognition is largely opaque here.
  - Coordination is centrally scheduled and round-based, not adaptive decentralized negotiation/swarm control.
  - Some robustness issues are handled heuristically (JSON repair, retries), suggesting brittle LLM-output handling.
  - Significant coupling to file-based IPC and local paths may limit distributed deployment or strict fault tolerance.
  - Testing coverage for complex multi-agent dynamics appears limited in this repo (few simulation-focused tests).

- **Research relevance:**
  - Useful evidence of a production-oriented **LLM social simulation pipeline** with explicit multi-agent coordination.
  - Demonstrates manager-script orchestration of many LLM agents with measurable action traces over time.
  - Illustrates integration of graph memory updates from simulated actions into a persistent knowledge graph.
  - Good case study for comparing generated-agent ecosystems (OASIS/CAMEL) vs planner-executor agent stacks.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
