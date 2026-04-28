---
repo_name: NovaSky-AI/SkyRL
url: "https://github.com/NovaSky-AI/SkyRL"
stars: 1778
forks: 306
contributors_count: 76
last_commit_date: "2026-04-23T01:07:03+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-04-27T14:18:04.526133+00:00"
model: auto
duration_s: 88.3
clone_size_kb: 43198
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`SkyRL` is primarily a reinforcement-learning library for training LLMs, and its `skyrl-agent` subpackage provides an agent runtime used to generate/evaluate tool-using trajectories for RL. In practice, users run task configs (YAML) via `AutoAgentRunner` to execute many agent trajectories over datasets, then compute rewards for training/eval (e.g., web-research tasks). The runtime instantiates an agent class (`ReActAgent` or `OHCodeActAgent`), executes iterative tool-calling loops, and post-processes transitions into training-ready tensors/metrics (`skyrl-agent/skyrl_agent/agents/base.py:113-692`). So the delivered output is not just chat responses; it is batched rollout data (messages, transitions, rewards, masks, metrics) used in RL pipelines.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen in core runtime (no such imports found in code search). The agent stack is mostly **custom orchestration** plus optional **OpenHands** integration for one agent type (`skyrl-agent/skyrl_agent/agents/oh_codeact/codeact_agent.py:15-47`). Agent selection is registry-driven: `AutoAgentRunner` reads task YAML, maps `agent_cls` to a runner/trajectory class, and creates the configured runtime (`skyrl-agent/skyrl_agent/auto.py:15-33`, `skyrl-agent/skyrl_agent/agents/mapping.py:1-9`).

The main intelligence loop for ReAct lives in `ReActAgent`: prepare prompt from message history, call async inference backend, parse tool call, execute tool, append observation, and iterate until `finish` or stopping condition (`skyrl-agent/skyrl_agent/agents/react/react_agent.py:311-428`). Prompting logic is split between task-level instruction builders (e.g., `WebResearchTask.get_instruction`) and tool-specific system-prefix injection (`skyrl-agent/skyrl_agent/tasks/web_research_task.py:22-95`, `skyrl-agent/skyrl_agent/agents/react/react_agent.py:445-487`).

Architecturally, this is “many independent single-agent trajectories” rather than multi-role teams. `AgentRunner` creates multiple trajectories per instance and dispatches them concurrently; each trajectory contains one agent loop and one evaluator (`skyrl-agent/skyrl_agent/agents/base.py:190-234`, `629-692`).

## 3. Orchestration Pattern

Closest match: **sequential per-agent loop + batched async orchestration across trajectories** (an “other/hybrid” pattern).  
- Inside each agent: strictly sequential ReAct cycle (LLM -> parse tool call -> execute tool -> continue/finish).  
- Across dataset/trajectories: dispatcher runs many trajectory pipelines concurrently (`async_batch` or `async_pipeline`).

Example (single-agent control flow, sequential):
`skyrl-agent/skyrl_agent/agents/react/react_agent.py:331-390`
```python
response_str, meta_info = await self._generate_with_recording(...)
...
tool_call, parse_error = parse_tool_call(response_str, self.tool_params)
...
output = await self._execute_tool(tool_name, tool_args, tool_call_id)
if tool_name == "finish":
    result = StepResult.finished("FINISH_TOOL", output)
else:
    result = StepResult.continuing(response_str)
    if output is not None:
        self._append_tool_output(output, tool_call_id)
```

Example (batch orchestration across trajectories):
`skyrl-agent/skyrl_agent/dispatcher/dispatchers.py:109-120`
```python
async def one_traj(instance_id, trajectory_id):
    traj = trajectories[instance_id][trajectory_id]
    if init_fn is not None:
        await getattr(traj, init_fn)()
    await getattr(traj, run_fn)()
    await getattr(traj, eval_fn)()

...
tasks.append(asyncio.create_task(one_traj(instance_id, trajectory_id)))
await asyncio.gather(*tasks)
```

## 4. Tools & External Integrations

- **Inference APIs / model serving**
  - OpenAI-compatible HTTP backend for `/v1/completions` and `/v1/chat/completions` (`skyrl-agent/skyrl_agent/integrations/openai.py:20-77`).
  - Additional backend plumbing via integration registry used by `AgentRunner` (`skyrl-agent/skyrl_agent/agents/base.py:124-131`).

- **Web search APIs**
  - Serper Google API (`https://google.serper.dev/search`) in `SearchEngine` (`skyrl-agent/skyrl_agent/tools/search_engine.py:55-99`).
  - You.com API (`https://api.ydc-index.io/v1/search`) in `YouComSearchEngine` (`skyrl-agent/skyrl_agent/tools/youcom_search_engine.py:96-137`).
  - Local search HTTP service via `LOCAL_SEARCH_URL` (`skyrl-agent/skyrl_agent/tools/local_search.py:28-65`).

- **Browser/content retrieval + summarization**
  - `web_browser` fetches pages via Jina reader (`https://r.jina.ai/...`) and summarizes content using an OpenAI-compatible model endpoint (`WEB_SUMMARY_API_BASE`) (`skyrl-agent/skyrl_agent/tools/web_browser.py:535-563`, `340-349`, `490-507`).

- **Code execution / terminal-like sandbox**
  - `code_interpreter` tool posts code to Sandbox Fusion (`SANDBOX_FUSION_URL + /run_code`) for execution (`skyrl-agent/skyrl_agent/tools/sandbox_fusion.py:70-78`).

- **OpenHands agent integration**
  - `OHCodeActAgent` imports OpenHands controller/agent/action stack and can execute OpenHands-style actions/tools (`skyrl-agent/skyrl_agent/agents/oh_codeact/codeact_agent.py:15-35`, `223-232`).

- **Task verification via LLM judge**
  - Web/STEM judge used in evaluation (`skyrl-agent/skyrl_agent/tasks/web_research_task.py:215-234`).

## 5. Notable Code Walkthrough

- `skyrl-agent/skyrl_agent/agents/react/react_agent.py:39-499`  
  Core ReAct implementation: tool registration, incremental message/token handling, robust parsing/error recovery, tool invocation, and iterative stop conditions.

- `skyrl-agent/skyrl_agent/agents/base.py:113-692`  
  Main runtime orchestrator (`AgentRunner`): builds infer backend, initializes per-instance/per-trajectory objects, invokes dispatcher, then converts trajectories into RL training outputs and rollout metrics.

- `skyrl-agent/skyrl_agent/dispatcher/dispatchers.py:20-123`  
  Defines async dispatch modes (`async_pipeline`, `async_batch`) that parallelize trajectory lifecycle stages (init/run/eval).

- `skyrl-agent/skyrl_agent/tasks/web_research_task.py:22-249`  
  Task prompt/eval logic for browser-search workflows: injects system instructions for tool sequencing and evaluates outputs with dataset-aware judge logic.

- `skyrl-agent/skyrl_agent/tools/web_browser.py:14-747`  
  Largest external-tool bridge: URL normalization, blocking policies, Jina fetch, chunked extraction, and LLM summarization pipeline for page content.

## 6. Use-Case Mapping

The assigned use case `Browser / Terminal Use` is **partly correct but incomplete**. The repo does include browser/search and sandbox code-exec tools (`web_browser`, `search_engine`, `code_interpreter`) and can run tool-using trajectories for web research. However, the broader project is chiefly an RL training/orchestration system for many task types, where agentic browser/terminal behavior is one workload among others (`skyrl-agent/skyrl_agent/agents/base.py:629-692`, `skyrl-agent/examples/run_skyrl/skyrl_web_research_hle.yaml:1-42`). The better top-level label is **Workflow Automation**: configurable batched rollouts, async dispatch, evaluation, and training-data generation pipelines.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong modularity via registries for agents, trajectories, tasks, dispatchers, and tools (`auto.py`, `mapping.py`, `dispatchers.py`, `tools/base.py`).
  - Practical high-throughput async rollout orchestration (batch/pipeline dispatcher modes).
  - Robust tool-call loop with explicit error classes and recovery prompts in ReAct runtime.
  - End-to-end RL-oriented output generation (transitions, masks, rewards, rollout metrics), not just inference.
  - Rich external tool ecosystem (search, web fetch/summarization, sandbox execution, OpenHands integration).

- **Limitations:**
  - Runtime is mostly single-agent-per-trajectory; little evidence of coordinated multi-role agent collaboration.
  - Heavy reliance on environment variables/external services (API keys/endpoints) can make reproducibility brittle.
  - Some tools raise at import/init time when env vars are missing (e.g., `search_engine` key requirement), reducing graceful degradation.
  - Considerable complexity and side effects in tool code (large monolithic `web_browser`), which may hinder maintainability/testing.
  - Evaluation logic is task-conditional and partly heuristic; may introduce dataset-specific coupling.

- **Research relevance:**
  - Useful evidence for **agentic RL data generation** pipelines (tool-use trajectories -> reward -> training tensors).
  - Demonstrates scalable orchestration of many asynchronous agent rollouts with pluggable dispatch strategies.
  - Illustrates production-style tool-augmented ReAct agents with robust parsing/recovery patterns.
  - Serves as a case study in combining custom agent loops with external agent frameworks (OpenHands) in one stack.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
