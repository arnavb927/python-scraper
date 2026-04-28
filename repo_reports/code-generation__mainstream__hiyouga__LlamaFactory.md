---
repo_name: hiyouga/LlamaFactory
url: "https://github.com/hiyouga/LlamaFactory"
stars: 70498
forks: 8615
contributors_count: 267
last_commit_date: "2026-04-22T11:44:01+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T09:20:30.350488+00:00"
model: auto
duration_s: 85.6
clone_size_kb: 18446
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`LlamaFactory` is a unified CLI/WebUI framework for fine-tuning, evaluating, exporting, and serving many open LLM/VLM checkpoints, rather than a multi-agent runtime framework. Users typically run commands like `llamafactory-cli train`, `llamafactory-cli chat`, `llamafactory-cli api`, or launch the Gradio WebUI, and the system orchestrates model loading, dataset/template processing, training stages (SFT/DPO/PPO/etc.), and inference backends. The main output is trained/adapted model artifacts (checkpoints/adapters), plus inference endpoints (OpenAI-style API) and interactive chat interfaces. It solves end-to-end LLM workflow management (training/inference/deployment plumbing) for practitioners who do not want to hand-wire each component.

## 2. Agent Framework & Architecture

This repo does **not** use LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, or a custom multi-agent planner/worker runtime. I found no such framework imports in source code, and dependencies are centered on `transformers`, `trl`, `accelerate`, `torch`, `gradio`, `fastapi`, `ray`, and inference backends (`vllm`, `sglang`) (`pyproject.toml:38-76`).

Architecture is a command-driven orchestrator: the CLI entrypoint dispatches to train/chat/api/webui modes (`src/llamafactory/launcher.py:38-179`), training routes through stage-specific functions (`src/llamafactory/train/tuner.py:62-137`), and inference routes through a single `ChatModel` wrapper that selects one backend engine (`HF`, `vLLM`, `SGLang`, `KTransformers`) (`src/llamafactory/chat/chat_model.py:47-85`). “Intelligence” lives inside the underlying LLM plus prompt/template formatting, not in agent coordination logic (`src/llamafactory/data/template.py:40-170`).

There is tool-calling support (formatting/parsing function calls) for single-model inference, but it is still one assistant model producing tool-call tokens; no planner/worker or multi-role agent team is executed at runtime (`src/llamafactory/data/tool_utils.py:123-211`, `src/llamafactory/api/chat.py:217-234`).

## 3. Orchestration Pattern

Closest match: **other (single-controller workflow orchestration)**, not MAS.

Control flow is centralized in a command router:

```python
# src/llamafactory/launcher.py:136-167
elif command == "api":
    from .api.app import run_api
    run_api()
elif command == "chat":
    from .chat.chat_model import run_chat
    run_chat()
elif command == "train":
    from .train.tuner import run_exp
    run_exp()
```

Training then follows sequential stage dispatch (pt/sft/rm/ppo/dpo/kto), with optional Ray distributed execution:

```python
# src/llamafactory/train/tuner.py:102-137
elif finetuning_args.stage == "sft":
    run_sft(...)
elif finetuning_args.stage == "ppo":
    run_ppo(...)
...
if ray_args.use_ray:
    _ray_training_function(...)
else:
    _training_function(...)
```

So this is a procedural pipeline coordinator, not a graph/swarm/hierarchical agent system.

## 4. Tools & External Integrations

- **Inference backends (`vLLM`, `SGLang`, HuggingFace, KTransformers)** wired in `ChatModel` backend selection (`src/llamafactory/chat/chat_model.py:50-85`) and concrete engines (`src/llamafactory/chat/vllm_engine.py:46-110`, `src/llamafactory/chat/sglang_engine.py:87-129`).
- **OpenAI-style API service (FastAPI + Uvicorn + SSE)** in `create_app`/`run_api` (`src/llamafactory/api/app.py:69-134`).
- **Function/tool-calling protocol formatting/parsing** via tool utilities and template extraction (`src/llamafactory/data/tool_utils.py:123-907`, `src/llamafactory/data/template.py:88-91`), exposed through API chat completion handling (`src/llamafactory/api/chat.py:169-178`, `217-234`).
- **Distributed training / cluster execution** via `torchrun` launch and optional Ray workers (`src/llamafactory/launcher.py:60-134`, `src/llamafactory/train/tuner.py:263-327`).
- **Web UI process orchestration** (Gradio + subprocess-managed training jobs) (`src/llamafactory/webui/runner.py:357-460`).
- **Model/data ecosystem integrations**: Hugging Face hub push/export in training/export path (`src/llamafactory/train/tuner.py:183-229`), plus optional experiment reporting hooks (e.g., SwanLab in WebUI args) (`src/llamafactory/webui/runner.py:269-275`).
- **Not present**: MCP servers, browser automation (Playwright/Browserbase), vector DB/RAG retrieval stack, shell-agent tool use.

## 5. Notable Code Walkthrough

- `src/llamafactory/launcher.py:38-179` - Central command dispatcher for all user-facing modes (`train`, `chat`, `api`, `webui`), including distributed launch behavior.
- `src/llamafactory/train/tuner.py:62-137` - Core training orchestration: parses args, installs callbacks, routes to stage-specific trainers, and optionally switches to Ray execution.
- `src/llamafactory/chat/chat_model.py:47-170` - Unified chat abstraction selecting runtime engine (HF/vLLM/SGLang/KT) and exposing sync/async chat/stream/score APIs.
- `src/llamafactory/api/chat.py:73-178` - Converts OpenAI-style request payloads (including multimodal inputs/tools) into internal message format and model inputs.
- `src/llamafactory/data/tool_utils.py:123-211` - Implements tool prompt schemas and function-call extraction/formatting logic for multiple model families.

## 6. Use-Case Mapping

The assigned primary use case (**Code Generation**) is only partially accurate. The codebase is broader: it automates **LLM workflow operations** (training, fine-tuning stages, distributed execution, export, inference serving, UI-driven experiment runs). It can absolutely be used to train/serve code models, but the repository itself is not mainly an autonomous code-generation agent system; it is a workflow platform for model lifecycle tasks. A better category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Unifies many training regimes (PT/SFT/RM/PPO/DPO/KTO) behind one CLI/WebUI orchestrator.
  - Strong backend flexibility for inference (`HF`, `vLLM`, `SGLang`, `KT`) with common interface.
  - Practical production hooks (OpenAI-style API, distributed training launch, model export/hub push).
  - Extensive template/tool-format support across many model families.
  - Good operational ergonomics for non-expert users (single entrypoint + WebUI).

- **Limitations:**
  - No true multi-agent runtime (no planner-worker graph, role-based debate, or agent swarm coordination).
  - Tool calling is mostly prompt/schema formatting + output parsing, not full tool-execution orchestration loops.
  - Architecture complexity is high and spread across many modules, increasing maintenance burden.
  - Limited built-in RAG/vector-store orchestration despite some tool-use and multimodal support.
  - Some behavior is backend-specific and can diverge (feature parity gaps across HF/vLLM/SGLang).

- **Research relevance:**
  - Strong evidence for **workflow orchestration around LLM lifecycle**, not MAS interaction protocols.
  - Useful case study for backend abstraction layers over heterogeneous model-serving engines.
  - Useful for studying practical tool-call schema normalization across model families.
  - Relevant to RLHF/finetuning pipeline engineering at open-source scale.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
