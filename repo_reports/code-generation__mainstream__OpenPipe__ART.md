---
repo_name: OpenPipe/ART
url: "https://github.com/OpenPipe/ART"
stars: 9224
forks: 805
contributors_count: 24
last_commit_date: "2026-04-22T21:04:52+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 8
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents]
generated_at: "2026-04-27T09:48:20.405807+00:00"
model: auto
duration_s: 101.5
clone_size_kb: 42183
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

OpenPipe ART is a Python framework for collecting trajectories from LLM-agent rollouts and training models with RL/SFT on those trajectories. In practice, users run custom `rollout(...)` functions (examples include MCP tool-use and self-play games), gather trajectory groups, score them, and call backend training (`LocalBackend` or `ServerlessBackend`) to produce improved checkpoints. The project solves the “agent on-the-job training” problem: preserve tool-calling/message traces, attach rewards/metrics, then fine-tune iteratively. The output is not an end-user chatbot app; it is a training pipeline that yields trained model checkpoints plus logged trajectory/metric artifacts.

## 2. Agent Framework & Architecture

The repo is **primarily custom**, not CrewAI/AutoGen/LlamaIndex.  
I found no runtime imports of CrewAI/AutoGen orchestration frameworks in `src`; instead ART defines its own primitives (`Trajectory`, `TrajectoryGroup`, gather/train backends). LangGraph is supported as an **integration layer** via wrappers in `src/art/langgraph/*` (e.g., `ChatOpenAI`, LangChain message conversion), not as ART’s core orchestration runtime (`src/art/langgraph/llm_wrapper.py:10-20`, `src/art/langgraph/message_utils.py:4-12`).

Architecture-wise, “intelligence” mostly lives in user rollout code (prompts, tool loop, reward logic), while ART handles capture/training infra. `Trajectory` holds conversation/tool traces and rewards; `gather_trajectory_groups(...)` runs many rollouts concurrently and aggregates metrics (`src/art/trajectories.py:38-47`, `src/art/gather.py:14-27`). `LocalBackend`/`ServerlessBackend` then train and emit metrics/checkpoints (`src/art/local/backend.py:577-619`, `src/art/serverless/backend.py:193-219`).

For LangGraph users, ART wraps model calls to log LangGraph interactions and reconstruct trainable trajectories (`wrap_rollout`, `LoggingLLM`) rather than building graphs itself (`src/art/langgraph/llm_wrapper.py:95-107`, `130-162`).

## 3. Orchestration Pattern

Closest match: **Other (turn-based + tool-loop orchestration)**, with optional **workflow-style parallel data collection**.

- In MCP example rollouts, control flow is a single-agent iterative tool loop: LLM proposes tool calls, code executes MCP tools, appends tool outputs, repeats until `complete_task` or turn limit (`examples/mcp-rl/mcp_rl/rollout.py:140-190`).
- At training time, ART orchestrates many rollouts concurrently and applies per-group scoring/training callbacks (`src/art/gather.py:40-50`).

Example control flow excerpts:

```python
# examples/mcp-rl/mcp_rl/rollout.py:141-149,167-173
while num_turns < scenario.max_turns and not task_completed:
    response = await client.chat.completions.create(...)
    choice = response.choices[0]
    traj.messages_and_choices.append(choice)
    if choice.message.tool_calls:
        for tool_call in choice.message.tool_calls:
            ...
```

```python
# src/art/gather.py:40-50
async def group_forward(g):
    group = await wrap_group_awaitable(g)
    if group is None or after_each is None:
        return group
    return await after_each(group)

future = asyncio.gather(*[group_forward(g) for g in groups])
```

There is also true multi-agent turn-taking in self-play examples (`x_model` vs `o_model`) (`examples/tic_tac_toe_self_play/rollout.py:112-117,155-173`).

## 4. Tools & External Integrations

- **OpenAI-compatible chat APIs**: rollouts and managed model clients call `chat.completions.create` (`examples/mcp-rl/mcp_rl/rollout.py:152-158`, `src/art/model.py:274-313`).
- **LangGraph/LangChain integration**: wrapper `LoggingLLM` bridges LangChain messages/tools to ART trajectories (`src/art/langgraph/llm_wrapper.py:10-15,130-136`; `src/art/langgraph/message_utils.py:54-90`).
- **MCP servers (Model Context Protocol)**: stdio MCP client session, `list_tools`, `call_tool` in rollout (`examples/mcp-rl/mcp_rl/rollout.py:14-16,74-81,188-191`).
- **W&B / Weave**: experiment tracking and artifact-backed checkpointing (`src/art/model.py:518-567`; `src/art/serverless/backend.py:448-471`; `examples/mcp-rl/mcp_rl/train.py:10,28-31`).
- **S3 (via AWS CLI)**: checkpoint/model sync helpers (`src/art/utils/s3.py:65-75,95-124,223-264`).
- **Local vLLM/OpenAI server process**: local backend starts/monitors model-serving endpoint (`src/art/local/backend.py:480-494,495-513`).
- **HuggingFace tokenization/preprocessing**: local RL/SFT packing/tokenization before training (`src/art/local/backend.py:333-351,796-810,937-949`).

No first-class browser automation or vector DB/RAG store wiring is present in core `src`.

## 5. Notable Code Walkthrough

- `src/art/trajectories.py:30-73,97-127` - Core data model (`History`, `Trajectory`) and conversion of mixed user/assistant-choice records into trainable message format. This is the canonical structure all rollouts feed into.
- `src/art/gather.py:14-66,140-180` - Concurrent orchestration layer for large rollout batches; handles exceptions, progress, and metric aggregation hooks (`after_each`) that enable reward/scoring pipelines.
- `src/art/langgraph/llm_wrapper.py:95-127,130-200` - LangGraph bridge that wraps `ChatOpenAI`, logs each invocation, preserves tools, and reconstructs trajectories from LangGraph runs.
- `examples/mcp-rl/mcp_rl/rollout.py:72-95,140-214` - Representative real-world agent loop: discovers MCP tools, lets LLM decide calls, executes tool calls, and appends tool outputs back into the conversation.
- `src/art/local/backend.py:577-619,775-905` - Local RL training backend: validates train params, packs trajectories to tensors, runs trainer/service, and emits per-step metrics/checkpoint info.

## 6. Use-Case Mapping

The assigned use case (**Code Generation**) is not the best fit for this repository’s core. ART is a **training/orchestration framework for tool-using agents**, not a code-assistant product where the primary runtime output is generated code. Its examples focus on task completion loops (MCP task automation, game self-play) and iterative policy improvement over trajectories (`examples/mcp-rl/mcp_rl/rollout.py`, `examples/mcp-rl/mcp_rl/train.py`). A better category is **Workflow Automation**: orchestrate repeated agent rollouts, scoring, and training in a structured pipeline.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear separation between rollout logic and training backend abstractions (`src/art/model.py`, `src/art/local/backend.py`, `src/art/serverless/backend.py`).
  - Strong trajectory-centric design (messages, tools, additional histories, rewards) for RL reproducibility (`src/art/trajectories.py`).
  - Practical integrations for real agent workloads: MCP, LangGraph, OpenAI-compatible APIs, W&B/S3.
  - Concurrent gather pipeline with per-group postprocessing hooks supports scalable data collection (`src/art/gather.py`).
  - Supports both local and hosted/serverless training paths with similar interfaces.

- **Limitations:**
  - Multi-agent coordination is mostly in examples; core runtime is not a dedicated MAS framework with explicit role routing/planning primitives.
  - Control logic (prompts/tool policies/reward heuristics) is highly user-script dependent, so reproducibility quality varies by rollout script.
  - No built-in safety/guardrail layer for tool execution beyond what rollout authors implement.
  - Heavy operational dependencies (W&B, AWS CLI/S3, model-serving infra) increase setup complexity.
  - LangGraph support is wrapper-style logging/capture, not native graph-construction/inspection within ART.

- **Research relevance:**
  - Good evidence for “agent trajectory RL engineering” in practical tool-use settings.
  - Useful case study in bridging external agent runtimes (LangGraph/MCP) into a unified RL data schema.
  - Demonstrates batch asynchronous rollout orchestration + reward scoring pipelines in production-oriented code.
  - Provides examples of both single-agent tool loops and turn-based multi-agent self-play rollouts.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
