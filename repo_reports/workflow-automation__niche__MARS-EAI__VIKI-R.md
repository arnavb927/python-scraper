---
repo_name: MARS-EAI/VIKI-R
url: "https://github.com/MARS-EAI/VIKI-R"
stars: 86
forks: 0
contributors_count: 3
last_commit_date: "2026-04-02T04:08:43+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 1
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T18:10:04.057974+00:00"
model: auto
duration_s: 112.8
clone_size_kb: 26218
uses_mas: no
final_use_case: Simulation
---
## 1. Overview

`MARS-EAI/VIKI-R` is primarily a research codebase for training and evaluating a vision-language model to produce **multi-robot action plans** (and trajectories) for embodied tasks, not a generic app-style agent platform. In practice, users run evaluation scripts such as `eval/VIKI-L1/qwen.py`, `eval/VIKI-L2/qwen.py`, or `eval/VIKI-L3/qwen.py`, which send image+task prompts to an OpenAI-compatible model endpoint and save prediction/score files. Training is done through the vendored `verl` PPO pipeline (`verl/verl/trainer/main_ppo.py`) with custom reward functions for plan correctness/format. The output is benchmark metrics (accuracy or trajectory errors), JSON result dumps, and stats files rather than an interactive assistant workflow.

## 2. Agent Framework & Architecture

No LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex framework appears in the code imports; this repo uses a **custom pipeline** built from:
- OpenAI-compatible chat completions for inference (`eval/VIKI-L*/qwen.py`, `eval/eval_with_fb/gpt4o.py`)
- A custom plan parser/scorer and simulator (`verl/verl/utils/reward_score/...`)
- The `verl` PPO training stack with Ray workers (`verl/verl/trainer/main_ppo.py`)

Architecturally, “multi-agent” in this repo mostly means **multiple embodied robots in the predicted plan**, not multiple LLM agents coordinating at runtime. A single model call is prompted to output a multi-robot plan in `<think>`/`<answer>` format and structured JSON-like steps (`eval/VIKI-L2/qwen.py:104-165`). That output is then transformed and validated by a symbolic simulator/evaluator (`verl/verl/utils/reward_score/viki_2.py:57-133`, `.../utils/eval/eval.py:167-251`).

The main “intelligence” is split between (a) model prompting for plan generation and (b) rule/simulation reward logic enforcing feasibility, temporal constraints, and goal constraints, which is then used for RL fine-tuning (`verl/verl/trainer/main_ppo.py:132-195`).

## 3. Orchestration Pattern

Closest match: **sequential pipeline (generate -> parse -> simulate/score -> optional retry)**, with parallelization over dataset samples via thread pools.

Control flow is straightforward in eval scripts: call model, compute score, aggregate stats (`eval/VIKI-L2/qwen.py:201-207`, `:243-301`), with optional retry + error feedback in `eval_with_fb`.

```241:251:verl/verl/utils/reward_score/utils/eval/eval.py
for commands in all_commands:
    step_commands = []    # commands in one step
    for command in commands:
        operation_name = command[0]
        ...
        is_available_action = self.checker.check_operation(...)
        if not is_available_action:
            self.error_desc_code = 'ACTION_NOT_FEASIBLE'
            return False
```

```206:243:eval/eval_with_fb/gpt4o.py
cot_response = generate_cot(task_description, robots_set, image_path, plan_answer, model)
res, error_desc = viki_2_re.compute_score(cot_response, ground_truth)
...
while res <= 0.1 and retry_count < max_retries:
    ...
    feedback_task = f"""{task_description} ... Error feedback: {error_desc} ..."""
    cot_response = generate_cot(feedback_task, robots_set, image_path, plan_answer, model)
    res, error_desc = viki_2_re.compute_score(cot_response, ground_truth)
```

## 4. Tools & External Integrations

- **OpenAI-compatible LLM API**: model inference via `OpenAI().chat.completions.create(...)` in `eval/VIKI-L1/qwen.py:19-20,90-99`, `eval/VIKI-L2/qwen.py:20,91-99`, `eval/VIKI-L3/qwen.py:45,74-82`, `eval/eval_with_fb/gpt4o.py:26,92-100`.
- **vLLM serving endpoint**: scripts are configured for local API base URL (`http://0.0.0.0:8000/v1`) and include comments for `vllm serve` usage (`eval/VIKI-L1/qwen.py:19,187-188`; `eval/VIKI-L2/qwen.py:20,218-219`).
- **Parquet/JSON dataset I/O**: uses pandas parquet loading and writes JSON stats/results (`eval/VIKI-L*/qwen.py` loaders and save blocks).
- **Custom simulator + rule engine**: plan feasibility and goal checking via `Eval`, `Checker`, `SimEnv` (`verl/verl/utils/reward_score/utils/eval/eval.py`, `.../checker.py`, `.../env.py`).
- **RL training infrastructure**: Ray-distributed PPO workers and reward manager integration (`verl/verl/trainer/main_ppo.py:66-77,116-195`).
- **Experiment tracking**: configs set `report_to: wandb` (`configs/viki-1-3b.yaml:32`, similarly in L2/L3 configs).

No MCP servers, browser automation, terminal-agent execution, or vector DB/RAG stack are wired as agent tools.

## 5. Notable Code Walkthrough

- `eval/VIKI-L2/qwen.py:104-216` - Core inference/evaluation loop for planning level: builds strict planning prompt, sends image+text to model, parses output, and scores with `viki_2.compute_score`. This is the clearest example of runtime “agentic” behavior in practice.
- `eval/eval_with_fb/gpt4o.py:171-259` - Adds iterative self-correction: failed plans are retried with explicit error feedback from the evaluator, forming a generate-evaluate-revise loop.
- `verl/verl/utils/reward_score/viki_2.py:87-133` - Converts model outputs into normalized action-step structures and computes combined format + execution correctness reward.
- `verl/verl/utils/reward_score/utils/eval/eval.py:167-251` - Executes stepwise command validation against constraints; this is the symbolic orchestrator that determines whether predicted multi-robot plans are actually feasible.
- `verl/verl/trainer/main_ppo.py:132-195` - Wires custom reward functions into the PPO trainer with Ray worker roles; shows how evaluation logic is used during RL fine-tuning.

## 6. Use-Case Mapping

The assigned label `Workflow Automation` is only a partial fit. The code automates an evaluation/training workflow over datasets (batch infer, score, retry, aggregate), but the substantive use case is **embodied multi-robot plan/trajectory prediction and simulation-style validation**. Concretely, the repo realizes this by generating structured multi-robot action plans from visual scenes (`eval/VIKI-L2/qwen.py`) and checking them in a simulated constraint environment (`verl/.../eval.py`, `checker.py`, `env.py`). A better category is **Simulation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong separation between generation and symbolic validation, enabling objective plan feasibility checks (`verl/.../eval.py`).
  - Explicit structured output contract (`<think>` + `<answer>` + action JSON) improves evaluability (`eval/VIKI-L2/qwen.py:105-136`).
  - Includes retry-with-feedback evaluation loop to study correction behavior (`eval/eval_with_fb/gpt4o.py:211-243`).
  - End-to-end RL training integration with custom reward functions in distributed PPO (`verl/trainer/main_ppo.py`).

- **Limitations:**
  - No true multi-LLM-agent runtime coordination; one model produces all roles/plans in a single response.
  - Prompting/parsing is brittle (regex + `ast.literal_eval`, occasional `eval`) and sensitive to formatting drift (`viki_2.py:44-55,103-110`).
  - Heavy hardcoded paths and evaluation settings reduce reproducibility portability (`eval/VIKI-L*/qwen.py` data paths/slices).
  - Sparse modularization in eval scripts (large monolithic files; repeated code across L1/L2/L3).

- **Research relevance:**
  - Good evidence for **symbolic execution-based reward shaping** in embodied multi-agent planning benchmarks.
  - Useful example of combining vision-language generation with constraint-based plan verification.
  - Supports studies on iterative repair via evaluator feedback loops in structured planning tasks.
  - Less relevant as evidence for decentralized or interacting LLM-agent systems.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Simulation
