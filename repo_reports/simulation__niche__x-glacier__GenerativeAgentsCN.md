---
repo_name: x-glacier/GenerativeAgentsCN
url: "https://github.com/x-glacier/GenerativeAgentsCN"
stars: 428
forks: 78
contributors_count: 3
last_commit_date: "2026-03-12T14:06:03+00:00"
primary_use_case: Simulation
user_tier: Niche
total_score: 2
architecture_labels: [Custom/Other]
use_case_labels: [Simulation]
generated_at: "2026-04-27T17:20:38.752069+00:00"
model: auto
duration_s: 73.5
clone_size_kb: 30309
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`x-glacier/GenerativeAgentsCN` is a Chinese refactor/localization of the Generative Agents simulation that runs a “small town” of autonomous personas over simulated time. Users run `generative_agents/start.py` to execute step-based simulation, which updates each persona’s plans, actions, movement, memories, and conversations, then writes checkpoints (`results/checkpoints/...`) for replay and analysis. The system also includes `compress.py` and `replay.py` to transform logs into timeline artifacts (`simulation.md`, `movement.json`) and visualize agent behavior in a Flask web UI. In practice, you get an agent society simulation where characters move, interact, chat, remember, and adapt daily behavior.

## 2. Agent Framework & Architecture

This repo is **custom multi-agent logic**, not LangGraph/AutoGen/CrewAI/LangChain orchestration. I found no imports of those frameworks; orchestration is implemented in project classes (`Game`, `Agent`) while LLM calls use `magentic` and memory retrieval uses `llama_index` (`generative_agents/modules/model/llm_model.py:6-7`, `generative_agents/modules/storage/index.py:5-12`).

Architecture is a simulation loop over many persona agents. `SimulateServer.simulate()` iterates steps and calls `game.agent_think(name, status)` for each configured persona (`generative_agents/start.py:71-88`). `Game` holds all agents in a shared world (`maze`) plus shared conversation log (`generative_agents/modules/game.py:20-38`), and each `Agent` has its own schedule, spatial memory, associative memory index, and prompt-building scratchpad (`generative_agents/modules/agent.py:27-36`).

Most “intelligence” lives in prompt templates + LLM completion wrappers. `Agent.completion()` dynamically dispatches to `Scratch.prompt_*` methods (schedule, reflection, chatting, action selection, etc.), sends prompt text to an LLM backend, and consumes typed outputs (`generative_agents/modules/agent.py:92-105`, `generative_agents/modules/prompt/scratch.py:45-845`). Long-term memory retrieval/ranking is handled by a custom `AssociateRetriever` over LlamaIndex vectors that blends recency/relevance/importance (`generative_agents/modules/memory/associate.py:76-113`).

## 3. Orchestration Pattern

Closest pattern: **other (simulation loop with decentralized peer agents)**.

Control is centrally stepped, but decision-making is per-agent and peer-reactive (not manager-worker, not graph state machine). The server loop drives each persona sequentially:

```137:147:generative_agents/start.py
for i in range(self.start_step, self.start_step + step):
    ...
    for name, status in self.agent_status.items():
        plan = self.game.agent_think(name, status)["plan"]
        agent = self.game.get_agent(name)
        ...
```

Within each agent turn, the agent perceives environment, plans, reflects, and may initiate interaction with another agent via shared `agents` dict:

```107:132:generative_agents/modules/agent.py
def think(self, status, agents):
    events = self.move(status["coord"], status.get("path"))
    plan, _ = self.make_schedule()
    ...
    if self.is_awake():
        self.percept()
        self.make_plan(agents)
        self.reflect()
```

Peer coordination happens via `_reaction()` / `_chat_with()` where one agent inspects perceived concepts tied to other agents and can start multi-turn dialogue that updates both agents’ schedules/memory (`generative_agents/modules/agent.py:459-485`, `501-594`).

## 4. Tools & External Integrations

- **LLM APIs (OpenAI-compatible + Ollama local server)**: `LLMModel` supports `openai` and `ollama` providers, calling `/chat/completions` for Ollama or `magentic` OpenAI chat model (`generative_agents/modules/model/llm_model.py:75-117`, `170-181`).
- **Prompt/structured generation via `magentic` + Pydantic schemas**: prompt functions define response schemas (`BaseModel`) for constrained outputs (booleans, schedules, tuples) (`generative_agents/modules/prompt/scratch.py:55-58`, `142-170`, `441-450`).
- **Vector memory store via LlamaIndex**: embeddings and vector retrieval for event/thought/chat memory (`generative_agents/modules/storage/index.py:17-50`, `109-127`).
- **Embedding backends**: HuggingFace, Ollama embeddings, OpenAI embeddings are selectable (`generative_agents/modules/storage/index.py:20-33`); default config uses Ollama embedding model (`generative_agents/data/config.json:24-29`).
- **Web replay service (Flask)**: simulation replay UI server (`generative_agents/replay.py:4`, `9-14`, `59-66`).
- **Filesystem persistence/checkpointing**: per-step JSON state and conversation logs are written/read from `results/checkpoints` (`generative_agents/start.py:96-101`, `110-134`).

No MCP servers, browser automation frameworks, shell tools, or external databases/vector DB services (e.g., Pinecone/Chroma/pgvector) are wired; vector storage is local through LlamaIndex persistence.

## 5. Notable Code Walkthrough

- `generative_agents/start.py:24-104` - Simulation entrypoint and main loop; creates game, iterates steps, calls each agent’s think cycle, and saves checkpoint + conversation snapshots.
- `generative_agents/modules/game.py:12-70` - World container that instantiates all agents from config and exposes `agent_think()` aggregator, returning both movement plan and rich introspection info.
- `generative_agents/modules/agent.py:107-149` - Core per-agent cognition cycle (`think`): move/update, schedule creation/decomposition, perception, planning, reflection, and path output.
- `generative_agents/modules/agent.py:501-594` - Multi-agent social behavior: chat initiation/termination logic, turn-taking dialogue generation, and synchronized schedule updates for both participants.
- `generative_agents/modules/prompt/scratch.py:21-29` and `45-845` - Prompt factory layer for almost all cognitive tasks (poignancy scoring, planning, routing to locations, dialogue, reflection), making this the main behavior-programming surface.
- `generative_agents/modules/memory/associate.py:76-113` - Custom memory retriever that reranks by recency, semantic relevance, and poignancy, critical for context selection before planning/chatting.

## 6. Use-Case Mapping

This repository clearly realizes **Simulation**. It simulates many autonomous personas in a shared environment with time progression, spatial movement, social interaction, memory updates, and replay visualization (`generative_agents/start.py:71-104`, `generative_agents/modules/agent.py:107-149`, `generative_agents/replay.py:59-66`). The assigned category appears correct; this is not primarily workflow automation or code generation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Rich end-to-end agent loop combining perception, planning, action, reflection, and dialogue in one coherent runtime (`modules/agent.py`).
  - Explicit long-term memory model with weighted retrieval (recency/relevance/importance), useful for believable continuity (`modules/memory/associate.py:92-110`).
  - Strong prompt modularization (`Scratch.prompt_*`) makes behavior tuning transparent and extensible without rewriting orchestration (`modules/prompt/scratch.py`).
  - Practical observability/reproducibility through checkpoint logs + replay tooling (`start.py`, `compress.py`, `replay.py`).
  - Multi-agent social coordination emerges from local policies rather than hardcoded scripts (`_reaction`, `_chat_with`).

- **Limitations:**
  - No robust central conflict resolution/scheduling mechanism; agents are stepped sequentially and may have order effects (`start.py:76-88`).
  - Heavy reliance on prompt heuristics/failsafes can reduce behavioral stability and scientific control (`scratch.py` widespread `failsafe` usage).
  - Limited failure handling for external model calls beyond retries; quality/latency/outage management is basic (`llm_model.py:36-55`).
  - Memory store is local and single-process; no distributed/shared memory backend for larger-scale experiments (`storage/index.py`).
  - Evaluation is mostly qualitative (replay/logs), with little built-in quantitative benchmarking.

- **Research relevance:**
  - Useful artifact for studying **LLM-driven social simulation** with memory-augmented agents in a shared world.
  - Demonstrates a concrete implementation of **decentralized multi-agent interaction** (peer chat/react loops) without heavyweight agent frameworks.
  - Offers a reproducible testbed for experiments on **prompt design + memory retrieval effects** on emergent behavior.
  - Provides a Chinese-localized baseline for cross-lingual studies of generative-agent behavior.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
