---
repo_name: ToolBrain/ToolBrain
url: "https://github.com/ToolBrain/ToolBrain"
stars: 166
forks: 14
contributors_count: 11
last_commit_date: "2026-04-08T03:44:19+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [LangChain, AutoGen, CrewAI]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T17:53:18.229863+00:00"
model: auto
duration_s: 84.3
clone_size_kb: 12495
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

ToolBrain is an RL training framework for **tool-using LLM agents**, not a ready-made end-user assistant. A user typically runs scripts such as `examples/01_run_hello_world.py` or `examples/07_email_search_agent/2_run_training_experiments.py` to instantiate an agent (SmolAgents or LangChain-backed), execute it on task datasets, score trajectories with reward functions, and update model weights via GRPO/DPO/supervised training. The output is a fine-tuned agent model (LoRA adapters + tokenizer) plus training/evaluation artifacts, rather than a deployed multi-agent application. In practice, it solves “how do I improve a tool-calling agent’s behavior over repeated tasks?” with a pluggable adapter + reward + optimizer pipeline.

## 2. Agent Framework & Architecture

Framework usage in code is: **SmolAgents (primary)**, **LangChain/LangGraph (adapter path)**, and **custom ToolBrain training logic**.  
- SmolAgents is concrete in `toolbrain/factory.py:144-167` (`CodeAgent`) and `toolbrain/adapters/smolagent/smolagent_adapter.py:29-53`.  
- LangChain/LangGraph is optional via `toolbrain/adapters/langchain/langchain_adapter.py:90-121` and `toolbrain/brain.py:276-283` (detecting `CompiledStateGraph`).  
- There is no real AutoGen/CrewAI runtime usage in source imports or execution paths.

Architecture is centered on `Brain`, which wraps a single executable agent and handles training strategy. `Brain` auto-selects an adapter (`SmolAgentAdapter` or `LangChainAdapter`), collects traces via `agent_adapter.run()`, computes rewards, and applies GRPO/DPO/Supervised updates (`toolbrain/brain.py:181-241`, `285-433`). The “intelligence” for control is mostly in prompting/tool-use behavior inside the underlying agent framework plus reward design in `toolbrain/rewards.py`.

A key structural detail: adapters normalize disparate agent memories into a common `Trace` schema (`toolbrain/core_types.py:24-40`), then RL modules optimize token-level policy objectives (`toolbrain/learning/grpo/algo.py`, `toolbrain/learning/dpo/algo.py`). So ToolBrain is best read as a **training/orchestration layer around one agent execution loop**, not a multi-agent planner system.

## 3. Orchestration Pattern

Closest match: **sequential single-agent training loop** (with optional tool-call substeps), i.e., “other” rather than graph-MAS orchestration.

Control flow is linear: dataset example -> collect one or more traces -> score -> update policy.
- `toolbrain/brain.py:390-417` shows `get_trace(...)` then algorithm-specific update.
- `toolbrain/brain.py:336-343` loops over `num_group_members` runs of the same agent to form a training batch, not multiple collaborating agents.

Excerpt 1 (`toolbrain/brain.py:336-341`):
```python
for i in range(num_group_members):
    trace, rl_input, raw_memory_steps = self.agent_adapter.run(query)
    traces.append(trace)
    rl_inputs.append(rl_input)
```

Excerpt 2 (`toolbrain/brain.py:409-417`):
```python
if self.algorithm in GRPOALiasNames:
    self.learning_module.train_step(rl_inputs, rewards)
elif self.algorithm in DPOALiasNames:
    chosen_segments, rejected_segments = make_dpo_pairs(rl_inputs, rewards)
```

Even when LangGraph is supported, it is used as an input agent type adapter, not as a ToolBrain-managed multi-agent graph runtime.

## 4. Tools & External Integrations

- **Agent frameworks / tool APIs**
  - SmolAgents `CodeAgent` integration in `toolbrain/factory.py:144-167`, adapter in `toolbrain/adapters/smolagent/smolagent_adapter.py`.
  - LangChain/LangGraph integration in `toolbrain/adapters/langchain/langchain_adapter.py`.
- **LLM providers**
  - Hugging Face local models via `TransformersModel` / `transformers` in `toolbrain/factory.py:58-85` and `toolbrain/adapters/langchain/langchain_adapter.py:55-88`.
  - OpenAI API for tool retrieval helper in `toolbrain/retriever.py:95-101`.
  - LiteLLM judge calls in `toolbrain/rewards.py:355-363`.
- **Parameter-efficient training stack**
  - LoRA/PEFT in `toolbrain/adapters/smolagent/smolagent_adapter.py:319-383` and `toolbrain/adapters/langchain/langchain_adapter.py:369-463`.
  - Optional Unsloth and bitsandbytes in `toolbrain/models.py` (indirect), `toolbrain/factory.py`, and `toolbrain/learning/grpo/algo.py:25-33,105-117`.
- **Data and storage integrations**
  - Hugging Face Datasets loading in `examples/07_email_search_agent/2_run_training_experiments.py:55-57`.
  - SQLite email corpus tools in `examples/07_email_search_agent/email_tools.py:37-54,90-267`.
- **RAG-like retrieval**
  - Tool retrieval/routing via LLM prompt selection in `toolbrain/retriever.py:27-49,65-119` (retrieves relevant **tools**, not document vectors).
- **No MCP/browser/shell control layer**
  - No Browserbase/Playwright/MCP runtime wiring found in core source.

## 5. Notable Code Walkthrough

- `toolbrain/brain.py:48-433` - Main orchestrator: auto-detects adapter type, gathers traces, computes rewards, and runs GRPO/DPO/supervised updates; this is the core training runtime.
- `toolbrain/adapters/smolagent/smolagent_adapter.py:68-237` - Executes a SmolAgent run and reconstructs high-fidelity trace + RL input segments from agent memory, enabling algorithm-agnostic optimization.
- `toolbrain/adapters/langchain/langchain_adapter.py:120-367` - Bridges LangGraph/LangChain agents into ToolBrain’s trace format and training interfaces; includes custom stream parsing for tool-call turns.
- `toolbrain/adapters/langchain/hf_tool_wrapper.py:37-135` - Implements prompt-based JSON tool calling for HuggingFace chat models, executes selected tools, and iterates until final answer.
- `examples/07_email_search_agent/2_run_training_experiments.py:117-223` - Most realistic end-to-end script: creates an email-search tool agent, selects reward mode, trains over dataset, runs periodic evaluation, and saves adapters.

## 6. Use-Case Mapping

The assigned label `RAG + Agents` is only **partially** accurate. This repo does include retrieval-style behavior (tool selection and email search over SQLite FTS), but the dominant implementation focus is **training and improving tool-using agents through RL workflows**. The strongest category fit is **Workflow Automation**: users automate repeated train/evaluate/save loops for agent policies (`examples/07_email_search_agent/2_run_training_experiments.py:146-223`), with configurable rewards and algorithms. Also, runtime generally centers on one acting agent rather than a coordinated multi-agent system.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear adapter abstraction that unifies SmolAgents and LangChain traces into one training schema (`toolbrain/adapters/*`, `toolbrain/core_types.py`).
  - Practical RL options (GRPO, DPO, supervised) with configurable reward functions (`toolbrain/brain.py`, `toolbrain/rewards.py`).
  - Good support for efficient fine-tuning (LoRA, optional Unsloth, bitsandbytes) in training adapters.
  - Includes realistic domain example (email search with SQLite + judge-based evaluation) rather than only toy math tasks.
  - Supports LLM-as-judge ranking reward for trajectory-level feedback (`toolbrain/rewards.py:304-400`).

- **Limitations:**
  - No true runtime multi-agent coordination (no planner-worker teams, debate, or swarm message passing).
  - “Tool retrieval” is prompt-based LLM selection, not robust vector/index retrieval infrastructure.
  - LangChain tool-calling path relies on custom JSON prompting/parsing, which can be brittle (`hf_tool_wrapper.py`).
  - Heavy dependence on external model/API behavior for retrieval and judging, with limited guardrails/retries.
  - Sparse explicit testing harness in repo root for core adapter/training correctness under regressions.

- **Research relevance:**
  - Useful evidence for **RL fine-tuning of tool-use agents** across multiple agent frameworks.
  - Demonstrates a concrete **trace-normalization interface** for cross-framework agent training.
  - Illustrates practical tradeoffs between rule-based rewards and LLM-judge rewards in agent learning loops.
  - Relevant as an engineering artifact for “agent training infrastructure,” less so for emergent multi-agent coordination science.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
