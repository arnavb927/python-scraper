---
repo_name: yhzhu99/MedAgentBoard
url: "https://github.com/yhzhu99/MedAgentBoard"
stars: 51
forks: 3
contributors_count: 5
last_commit_date: "2026-03-13T09:51:47+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 1
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T18:14:25.989590+00:00"
model: auto
duration_s: 66.7
clone_size_kb: 712
uses_mas: yes
final_use_case: Simulation
---
## 1. Overview

`yhzhu99/MedAgentBoard` is a benchmark implementation repo for comparing multiple multi-agent medical LLM workflows (plus single-LLM baselines) across three implemented tasks: medical QA/VQA, lay-summary generation, and EHR risk prediction. In practice, users run task-specific scripts like `python -m medagentboard.medqa.multi_agent_medagent ...` or batch runners such as `medagentboard/medqa/run.sh` and `medagentboard/ehr/run.sh`, which process dataset JSON files and emit per-sample result logs. Each run executes a multi-agent protocol (e.g., specialist panel, recruiter-moderator pipeline, confidence-weighted debate) and writes outputs including final predictions and full interaction history. The repo is therefore an experimental harness for agentic collaboration patterns rather than an end-user clinical application.

## 2. Agent Framework & Architecture

This project uses a **custom multi-agent framework** built directly on the OpenAI Python SDK (`from openai import OpenAI`) with provider-specific OpenAI-compatible endpoints configured in `medagentboard/utils/llm_configs.py:1-91`. I found no imports of LangGraph, LangChain, CrewAI, AutoGen, or LlamaIndex in the implementation files.

Architecture is implemented as several standalone orchestrators, each reproducing a different paper-style collaboration method. For example, MedAgent-style orchestration in `medagentboard/medqa/multi_agent_medagent.py:542-707` defines roles for expert gatherer, doctor agents, a meta synthesizer, and a final decision agent; ReConcile in `medagentboard/medqa/multi_agent_reconcile.py:372-625` defines peer agents plus a coordinator with multi-round discussion and weighted voting; MDAgents in `medagentboard/medqa/multi_agent_mdagents.py:358-1210` adds complexity classification and dynamic recruitment of experts/teams.

“Intelligence” is primarily prompt-driven: each role has explicit system prompts (e.g., specialist reasoning, synthesis, review, recruitment), JSON output constraints, and fallback parsers. Orchestration logic itself (round loops, consensus checks, weighted aggregation, team sequencing) is handwritten in Python classes, with per-item traces saved to logs.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) + staged sequential workflow** (with a few swarm-like discussion loops in specific methods).

In MedAgent-style code, control is explicitly manager-led: gather experts → specialists analyze → meta agent synthesizes → specialists review → decision agent finalizes (`medagentboard/medqa/multi_agent_medagent.py:612-684`).

```644:654:medagentboard/medqa/multi_agent_medagent.py
# Step 1: Gather relevant domain experts for this question
specialties = self.expert_gatherer.gather_question_domain_experts(question)
...
# Step 3: Meta agent synthesizes opinions without providing an answer
synthesis = self.meta_agent.synthesize_opinions(
    doctor_opinions, self.doctor_specialties, current_round
)
```

ReConcile uses a coordinator-driven iterative debate loop (initial responses, repeated discussion rounds, then weighted final vote), still centrally orchestrated (`medagentboard/medqa/multi_agent_reconcile.py:546-606`).

```567:576:medagentboard/medqa/multi_agent_reconcile.py
while round_num < self.max_rounds and not consensus_reached:
    round_num += 1
    discussion_prompt = self._group_answers(current_answers)
    new_answers = []
    for agent in self.agents:
        resp = agent.generate_discussion_response(
            question, discussion_prompt, options, image_path
        )
```

## 4. Tools & External Integrations

- **LLM APIs via OpenAI-compatible client**: all agents call `client.chat.completions.create(...)` (`medagentboard/medqa/multi_agent_medagent.py:60-89`, `medagentboard/ehr/multi_agent_reconcile.py:79-107`).
- **Multi-provider endpoint routing/config** (DeepSeek, DashScope/Qwen, Volcengine Ark): centralized in `medagentboard/utils/llm_configs.py:6-91`.
- **Environment variable loading** via `python-dotenv`: `medagentboard/utils/llm_configs.py:1-5`.
- **Image ingestion for multimodal QA**: image file → base64 data URL inserted into message payload (`medagentboard/medqa/multi_agent_medagent.py:249-255`, helper in `medagentboard/utils/encode_image.py`).
- **Filesystem JSON pipeline** for datasets/logs (load processed datasets, save per-sample outputs): `medagentboard/utils/json_utils.py` usage throughout, e.g., `medagentboard/medqa/multi_agent_colacare.py:857-917`.
- **No browser automation / MCP / vector DB / SQL DB / shell-tool agenting** found in runtime agent loops.

## 5. Notable Code Walkthrough

- `medagentboard/medqa/multi_agent_medagent.py:36-707` — Core specialist-consensus implementation: defines role classes, robust LLM call wrappers, and a round-based MDT consultation loop with dynamic expert selection and final decision synthesis.
- `medagentboard/medqa/multi_agent_mdagents.py:358-1210` — Most complex orchestrator: moderator classifies query complexity, recruiter instantiates experts or multi-team structures, and execution branches into basic/intermediate/advanced flows.
- `medagentboard/medqa/multi_agent_reconcile.py:372-625` — Coordinator-led debate protocol with grouped argument sharing, consensus checks, and confidence-recalibrated weighted voting for final answer.
- `medagentboard/laysummary/multi_agent_agentsimp.py:855-1023` — Multi-role document simplification pipeline (director/analyst/simplifier/supervisor/metaphor/terminology/proofreader) showing long-chain workflow automation over text transformation.
- `medagentboard/utils/llm_configs.py:6-91` — Critical runtime wiring of model keys to API keys, base URLs, and model names; effectively the provider abstraction layer used by all agent classes.

## 6. Use-Case Mapping

The repository operationalizes **workflow automation** in the sense of automating multi-step LLM collaboration pipelines over datasets: each sample is routed through predefined stages (role assignment, analysis, synthesis, review, finalization) and logged end-to-end (`medagentboard/medqa/run.sh:54-113`, `medagentboard/ehr/run.sh:51-73`). The lay-summary pipeline is especially explicit as a scripted document-processing workflow with role-specialized handoffs (`medagentboard/laysummary/multi_agent_agentsimp.py:912-1008`).

However, the repo is primarily a **benchmark of medical multi-agent reasoning workflows**, not a production clinical workflow engine. Also, the README explicitly points Task 4 clinical workflow automation to a separate repo (`README.md:12,52`). So the assigned category is partially valid for methodology, but the **better category for this specific codebase** is **Simulation** (evaluation sandbox for multiple agentic protocols across tasks).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Implements multiple distinct MAS paradigms in one codebase (MedAgent, ReConcile, MDAgents, AgentSimp) for comparative experiments (`medagentboard/medqa/*`, `medagentboard/ehr/*`, `medagentboard/laysummary/*`).
  - Strong role-prompt modularity and reusable base-agent patterns make protocols easy to inspect/modify.
  - Stores detailed per-case histories (rounds, opinions, synthesis, votes), useful for analysis and reproducibility.
  - Supports multimodal QA (text+image) and structured EHR prediction, not just plain chat tasks.
  - Uses provider-agnostic OpenAI-compatible routing, enabling diverse model backends without major code changes.

- **Limitations:**
  - Heavy reliance on prompt-following + JSON parsing; limited hard guarantees on schema correctness or agent behavior.
  - No formal graph engine/state machine; orchestration is custom and somewhat duplicated across files.
  - “Synchronous”/“iterative” options in some modules are weakly realized (pipeline dominates actual execution paths).
  - Minimal external-tool grounding (no retrieval system, calculators, DB reasoning, or tool-calling APIs beyond LLM endpoints).
  - Clinical workflow automation benchmark code is split to another repository, so this repo is incomplete for that task class.

- **Research relevance:**
  - Good evidence base for studying whether multi-agent coordination improves medical-task performance over single-LLM baselines.
  - Useful for comparing orchestration motifs (consensus rounds, weighted voting, recruiter-driven team formation).
  - Suitable for analyzing robustness of role prompting and consensus dynamics under different model mixtures.
  - Provides practical examples of “agent society” simulation over benchmark datasets with trace-level logs.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Simulation
