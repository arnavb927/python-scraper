---
repo_name: OpenBMB/MiniCPM
url: "https://github.com/OpenBMB/MiniCPM"
stars: 8831
forks: 571
contributors_count: 39
last_commit_date: "2026-02-11T13:54:45+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-05-05T07:59:52.956341+00:00"
model: auto
duration_s: 117.7
clone_size_kb: 199897
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`OpenBMB/MiniCPM` is primarily a model and inference repository for the MiniCPM family, but it also includes agent-oriented demos (notably `MiniCPM4-Survey` and `MiniCPM4-MCP`) that show how MiniCPM models can run tool-using workflows. In practice, users run Python scripts that host a retriever service (`FastAPI` + `FAISS`) and a generation loop (`vLLM`) to iteratively produce outputs such as long-form literature surveys. The core deliverable is not an agent framework library; it is runnable model demos where an LLM emits structured tool calls and consumes tool feedback to complete tasks. So the repo solves “efficient on-device/model-serving + applied tool-use workflows,” with survey generation as the most complete end-to-end agentic example.

## 2. Agent Framework & Architecture

The agent logic is **custom**, not LangGraph/CrewAI/AutoGen/LlamaIndex. I do see `LangChain` imports in an older standalone demo (`demo/minicpm/langchain_demo.py:32-37`), but that file is a simple RAG chain and not the main orchestration substrate. The central agent runtime is hand-rolled around `vLLM`, prompt templates, parser logic, and an HTTP tool environment (`demo/minicpm4/SurveyGeneration/src/generation/run.py:93-179`, `demo/minicpm4/SurveyGeneration/src/generation/buffer.py:510-610`).

High-level architecture in `MiniCPM4-Survey`:
- A single LLM “writer/planner” loop builds prompts from current state and retrieved summaries (`buffer.py` prompt builder).
- The model outputs a structured `<answer>` (survey update) plus `<tool_call>` (`search_engine` or `finalize`), parsed by regex/JSON logic (`buffer.py:639-784`).
- The runtime posts tool calls to a retriever service (`retriever.py`), gets back summaries, updates survey state, and repeats until done (`run.py:127-179`).

There are references to “Agent-Summary-*” in comments (`buffer.py:316-320`), but in this codebase snapshot those extra cooperating LLM agents are not actually instantiated in runtime code; the implemented path is one model loop + external retriever environment.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker), implemented as a sequential control loop**.  
Manager-like logic lives in `BufferManager` + `rollout_with_env`; worker-like role is the external tool environment (`search_engine` retriever endpoint).

Control flow excerpt 1 (`demo/minicpm4/SurveyGeneration/src/generation/run.py:135-171`):
```python
messagess_todo = buffer_manager.build_prompt_for_generator()
response_texts = await asyncio.to_thread(vllm_manager.chat, messagess_todo)
extracted_results = [BufferManager.parse_generator_response(x) for x in response_texts]
payload = {"tool_calls": [x["tool_call"] for x in extracted_results]}
async with session.post(url, json=payload) as resp:
    env_response_batched = await resp.json()
```

Control flow excerpt 2 (`demo/minicpm4/SurveyGeneration/src/retriever/retriever.py:73-107`):
```python
if tool_calls[i]["name"] == "search_engine":
    search_engine_indices.append(i)
elif tool_calls[i]["name"] == "finalize":
    finalize_indices.append(i)
...
search_task_results = await asyncio.gather(*tasks)
...
results.append({"search_keywords": search_keywords, "summarys": abstracts, "done": done})
```

This is not a graph runtime (no explicit state-machine framework) and not swarm/peer-to-peer.

## 4. Tools & External Integrations

- **Local retrieval tool (FAISS + embedding model)**: `search_engine` implemented via `FastAPI`, `faiss`, `AutoModel.encode_query`; wired in `demo/minicpm4/SurveyGeneration/src/retriever/retriever.py:1-45`, `133-165`.
- **HTTP tool environment call**: generator sends tool calls to retriever endpoint via `aiohttp` POST in `demo/minicpm4/SurveyGeneration/src/generation/run.py:162-171`.
- **Model inference backend**: `vLLM` used for iterative generation/chat in `run.py:60-91`; Hugging Face tokenizer used for setup/formatting.
- **WebSocket + FastAPI frontend bridge**: live updates pushed to UI in `run.py:36-53`, `182-212`.
- **Function-calling parser integration for vLLM OpenAI-compatible serving**: custom parser class `MiniCPMToolParser` in `demo/minicpm3/function_call/minicpm_tool_parser.py:24-147`.
- **MCP-style tool schema demo**: tool lists loaded from JSON and parsed from model output in `demo/minicpm4/MCP/generate_example.py:165-191` and `available_tool_example.json`.
- **Vector store RAG demo (separate path)**: `LangChain + Chroma` in `demo/minicpm/langchain_demo.py:32-37`, `273-278`, `352-355`.

## 5. Notable Code Walkthrough

- `demo/minicpm4/SurveyGeneration/src/generation/run.py:93-224`  
  Main orchestration loop: prompt construction, model generation, tool-call extraction, retriever invocation, state update, and termination logic. This is the operational heart of the survey agent.

- `demo/minicpm4/SurveyGeneration/src/generation/buffer.py:510-610`  
  Stateful manager that builds per-turn prompts and records trajectories (`answer`, `tool_call`, summaries, done flag). It effectively acts as the controller memory and policy wrapper.

- `demo/minicpm4/SurveyGeneration/src/generation/buffer.py:639-784`  
  Structured response parser enforcing `<think>`, `<answer>`, `<tool_call>` format and schema checks. This makes tool routing deterministic and robust to malformed outputs.

- `demo/minicpm4/SurveyGeneration/src/retriever/retriever.py:60-107,133-165`  
  Tool runtime service: dispatches `search_engine` vs `finalize`, performs FAISS retrieval over arXiv corpus, and returns summaries consumed by the generator loop.

- `demo/minicpm3/function_call/minicpm_tool_parser.py:24-74,150-218`  
  vLLM-compatible tool-call parser for MiniCPM output tags (`<|tool_call_start|>...`). Important for integrating MiniCPM into OpenAI-style tool-calling pipelines.

## 6. Use-Case Mapping

The repository’s strongest concrete realization of the assigned use case is the `MiniCPM4-Survey` pipeline: an LLM iteratively plans/writes sections and calls a retrieval tool to fetch paper evidence, i.e., a **RAG-driven tool-using agent loop** (`run.py` + `retriever.py` + `buffer.py`). However, the implemented runtime is mostly **single-agent orchestration with tools**, not clearly multiple cooperating LLM agents. Given actual code behavior, the best fit is closer to **Workflow Automation** (LLM-controlled multi-step workflow over retrieval/tool environment) than pure “RAG + multi-agent team.”

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear end-to-end executable loop from prompt -> tool call -> retrieval -> state update (`run.py`/`retriever.py`).
  - Strong structured-output discipline with parser validation and schema checks (`buffer.py:639-784`).
  - Practical integration with common serving stack (`vLLM`, `FastAPI`, `aiohttp`, `FAISS`).
  - Includes both inference demos and parser infrastructure for tool-calling interoperability (`minicpm_tool_parser.py`).
  - Demonstrates long-horizon iterative writing workflow rather than single-shot RAG.

- **Limitations:**
  - No explicit multi-agent runtime despite “multi-agent” phrasing in docs/comments; execution is predominantly one LLM agent.
  - Orchestration is custom and tightly coupled; limited modular abstractions for swapping planners/executors.
  - Error handling is basic (many broad `except` paths), which can hide failure modes in production.
  - Tool space is narrow in the survey pipeline (`search_engine`/`finalize` only), limiting generality.
  - Minimal built-in evaluation harness for full multi-turn agent behavior robustness in code (beyond demo/eval scripts).

- **Research relevance:**
  - Useful evidence for **LLM-as-controller over external tool environment** design patterns.
  - Shows practical structured tool-call parsing and enforcement in open-source model serving pipelines.
  - Illustrates iterative RAG workflow construction for long-form generation tasks.
  - Supports studies on trade-offs between custom orchestration loops and formal agent frameworks.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
