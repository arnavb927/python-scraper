---
repo_name: HITsz-TMG/AIGC-Claw
url: "https://github.com/HITsz-TMG/AIGC-Claw"
stars: 1149
forks: 151
contributors_count: 7
last_commit_date: "2026-04-23T03:45:33+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T15:27:56.874491+00:00"
model: auto
duration_s: 82.5
clone_size_kb: 63393
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

This repository is an AI film-production workflow system that automates idea-to-video generation through staged LLM-driven agents. In the actively maintained backend (`aigc-director/aigc-claw/backend`), a user starts a project via FastAPI (`/api/project/start`), then executes each stage (script, character design, storyboard, reference images, video clips, post-production) through streamed API calls. The output is persisted session artifacts plus generated images/videos on disk, ending with concatenated episode videos. There is also an older `FilmAgent` prototype that scripts multi-role prompt chains, but the production architecture is the staged API workflow engine.

## 2. Agent Framework & Architecture

The runtime is **custom multi-agent orchestration**, not LangGraph/CrewAI/AutoGen/LangChain. The orchestrator imports local agent classes (`ScriptWriterAgent`, `CharacterDesignerAgent`, etc.) and manages them via a custom enum/state machine (`aigc-director/aigc-claw/backend/core/orchestrator.py:17-48`, `:90-98`). `requirements.txt` includes FastAPI/openai/dashscope but no LangGraph/CrewAI-style framework packages (`aigc-director/aigc-claw/backend/requirements.txt:5-34`).

Architecture is a **six-agent pipeline**: script generation -> character/setting image design -> storyboard segmentation -> reference image generation -> clip generation -> video stitching. Each stage is implemented as an `AgentInterface.process()` subclass (`aigc-director/aigc-claw/backend/core/agents/base_agent.py:16-96`) and invoked by `WorkflowEngine.execute_stage()` (`.../orchestrator.py:405-497`).

“Intelligence” lives mostly in prompt templates + stage-specific logic: script/storyboard/reference agents call `LLM.query(...)`, parse/validate structured JSON outputs, and emit artifacts for downstream stages (`script_agent.py:261-337`, `storyboard_agent.py:170-236`, `reference_agent.py:721-766`). Cross-stage synchronization (e.g., storyboard -> reference/video clip lists) is handled centrally in orchestrator hooks (`orchestrator.py:254-353`).

## 3. Orchestration Pattern

Closest pattern: **sequential workflow automation with state-machine orchestration** (a staged pipeline with human-in-the-loop interventions), not a peer swarm.

Control flow is stage-ordered by `STAGE_ORDER` and `WorkflowEngine._get_next_stage(...)` (`orchestrator.py:41-48`, `:179-186`), with explicit stage execution and status transitions in `execute_stage(...)` (`:447-497`). User-triggered continuation moves to next stage via `/continue` (`api_server.py:795-800`) and `continue_workflow(...)` (`orchestrator.py:524-573`).

Example flow excerpt:

```405:414:aigc-director/aigc-claw/backend/core/orchestrator.py
async def execute_stage(self, state, stage, input_data, ...):
    agent = self.agents[stage]
    ...
    result = await agent.process(input_data, intervention=intervention)
```

```553:566:aigc-director/aigc-claw/backend/core/orchestrator.py
if current_status == "waiting" or current_status == "completed":
    state.status[current_stage_str] = "completed"
    next_stage = self._get_next_stage(state.current_stage)
    ...
    return {"status": "ready", "next_stage": next_stage.value, ...}
```

## 4. Tools & External Integrations

- **LLM providers (OpenAI/Gemini/DeepSeek/Qwen via DashScope)**: routed by model name in unified LLM client (`aigc-director/aigc-claw/backend/tool/llm_client.py:41-95`).
- **Optional web search during LLM calls**: `web_search` flag passed through `LLM.query(...)` and agent calls (`llm_client.py:41-47`, `script_agent.py:121-123`).
- **VLM evaluation/selection loops** for image quality checks and best-version selection (`character_agent.py:165-205`, `reference_agent.py:308-375`).
- **Image generation backends** (DashScope, JiMeng, Seedream, GPT/Sora image APIs) via `ImageClient` router (`tool/image_client.py:150-275`).
- **Video generation backends** (Wan, JiMeng, Kling, Seedance) via `VideoClient` router (`tool/video_client.py:116-126`, `:127-217`).
- **FFmpeg post-production** for clip concatenation (`core/agents/editor_agent.py:121-136`).
- **Filesystem artifact store** (`code/data/sessions/*.json`, result image/video folders) for state persistence and cross-stage data reuse (`orchestrator.py:101-105`, `:577-636`; multiple agent files).
- **FastAPI SSE streaming** for progress/heartbeat/stage-complete events (`api_server.py:289-399`, `:678-792`).

No MCP servers, vector DB, browser automation, or terminal-agent tools are wired into the runtime workflow.

## 5. Notable Code Walkthrough

- `aigc-director/aigc-claw/backend/core/orchestrator.py:29-187,405-573`  
  Defines workflow stages, in-memory + disk state model, stage dispatch, artifact synchronization, and continuation gating; this is the core coordinator.

- `aigc-director/aigc-claw/backend/core/agents/script_agent.py:72-116,243-337`  
  Stage-1 script authoring agent: prompts LLM, extracts structured JSON (characters/settings/episodes), supports continuation and intervention-confirm flows.

- `aigc-director/aigc-claw/backend/core/agents/reference_agent.py:468-830`  
  Stage-4 bridge between storyboard and visual assets: generates first-frame prompts via LLM, gathers asset references, runs image generation + VLM quality/selection loops concurrently.

- `aigc-director/aigc-claw/backend/core/agents/video_agent.py:225-432`  
  Stage-5 clip generation engine: builds per-segment video prompts, binds selected reference images, runs parallel video tasks, and writes selected versions back to session artifacts.

- `aigc-director/aigc-claw/backend/api_server.py:146-204,246-399,455-649`  
  Exposes the operational API: project init, stage execution stream, intervention endpoints, and artifact mutation/synchronization logic for human edits.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is correct. The system automates a long, multi-step creative production pipeline with explicit machine-managed stage transitions, artifact passing, retries, and human checkpoints. It is not just a chatbot: it coordinates multiple role-specialized agents and external generation services to transform an idea into structured scripts, visual assets, generated clips, and final stitched videos. This is a strong example of end-to-end workflow orchestration over heterogeneous AI tools.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent decomposition by production role (writer/designer/storyboard/reference/director/editor).
  - Robust artifact-centric orchestration with persistent session state and cross-stage synchronization hooks.
  - Practical human-in-the-loop controls (`intervene`, `continue`, per-asset regeneration, version selection).
  - Multi-provider model routing for LLM/VLM/image/video, enabling backend swap by model string.
  - Incremental progress streaming and partial-result preservation improve long-running workflow usability.

- **Limitations:**
  - Heavy reliance on brittle JSON parsing from LLM outputs; error handling exists but schema enforcement is weak.
  - Tight coupling to filesystem/session JSON rather than transactional data layer; concurrency/race risks remain.
  - No standardized agent framework abstractions (graph compilers, planner policies, tool protocol standards).
  - Quality loops (VLM score thresholds) are heuristic and may not generalize across models/styles.
  - Mixed legacy code presence (`FilmAgent`) may confuse maintainability and architecture clarity.

- **Research relevance:**
  - Evidence of **production-oriented hierarchical workflow MAS** rather than toy dialogue-only agents.
  - Good case study for **artifact-mediated coordination** and cross-stage consistency in agent pipelines.
  - Useful for studying **human intervention checkpoints** in long-horizon generative automation.
  - Illustrates **multi-model orchestration** (LLM + VLM + T2I + I2V + deterministic media post-processing).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
