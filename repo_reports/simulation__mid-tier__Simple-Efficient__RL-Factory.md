---
repo_name: Simple-Efficient/RL-Factory
url: "https://github.com/Simple-Efficient/RL-Factory"
stars: 1741
forks: 163
contributors_count: 30
last_commit_date: "2025-12-05T03:25:56+00:00"
primary_use_case: Simulation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Simulation]
generated_at: "2026-04-27T14:22:58.220045+00:00"
model: auto
duration_s: 75.3
clone_size_kb: 15068
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

RL-Factory is a reinforcement-learning post-training framework for teaching an LLM to do multi-turn tool use, rather than a typical end-user “agent app.” In practice, users run training scripts like `main_grpo.sh` / `main_ppo.sh` with an environment config (tools + reward function), and the framework rolls out model responses, executes tool calls, and computes rewards for RL updates (`README.md:83-94`, `envs/mmbase.py:143-210`). The core output is a better tool-calling policy model checkpoint, not a standalone chatbot product. It also includes optional evaluation and WebUI components, but the central workflow is RL training over tool-interactive trajectories.

## 2. Agent Framework & Architecture

This repo does **not** use CrewAI/LangGraph/AutoGen as its primary runtime. The actual stack is a **custom agent-loop architecture built on VeRL + Ray**, with tool/function-calling support from Qwen-Agent and MCP clients (`verl/experimental/agent_loop/agent_loop.py:203-321`, `envs/tool_manager/qwen3_manager.py:13-17`, `envs/utils/mcp_manager.py:53-171`).  

Architecturally, “agent intelligence” is mainly in:  
1) the base LLM policy being trained,  
2) tool schemas and parser logic for extracting `<tool_call>` blocks, and  
3) reward computation logic that scores trajectories (`verl/experimental/agent_loop/tool_agent_loop.py:59-134`, `verl/experimental/agent_loop/tool_parser.py:75-107`, `verl/trainer/ppo/reward.py:84-138`).  
The framework supports different loop types (single-turn and tool-enabled multi-turn) and dispatches them by `agent_name`, but these are loop implementations, not multiple cooperating LLM personas (`verl/experimental/agent_loop/agent_loop.py:271-320`).

There are multiple worker roles in distributed RL (actor/critic/reward workers), but that is distributed training infrastructure, not a runtime multi-agent society of planner/worker LLM agents.

## 3. Orchestration Pattern

Closest match: **sequential iterative loop (single-agent with tool feedback), plus distributed worker orchestration**.

Control flow is: generate assistant tokens -> parse tool calls -> execute tools (possibly parallel) -> append tool outputs -> continue generation until stopping conditions. This is a turn-by-turn control loop, not a graph router or peer swarm (`verl/experimental/agent_loop/tool_agent_loop.py:70-123`).

Example (LLM/tool alternating loop):
```92:103:verl/experimental/agent_loop/tool_agent_loop.py
# no tool calls -> break; else execute calls
_, tool_calls = await self.tool_parser.extract_tool_calls(response_ids)
if not tool_calls:
    break

tasks = []
for tool_call in tool_calls[: self.max_parallel_calls]:
    tasks.append(self._call_tool(tool_call))
with simple_timer("tool_calls", metrics):
    tool_responses = await asyncio.gather(*tasks)
```

Example (worker-level dispatch of agent loop type):
```286:320:verl/experimental/agent_loop/agent_loop.py
for agent_name, messages, trajectory in zip(agent_names, raw_prompts, trajectory_info, strict=True):
    tasks.append(
        asyncio.create_task(self._run_agent_loop(agent_name, messages.tolist(), sampling_params, trajectory))
    )
...
agent_loop_config = _agent_loop_registry[agent_name]
agent_loop = hydra.utils.instantiate(
    config=agent_loop_config,
    trainer_config=_DummyConfig(config=self.config),
    server_manager=self.server_manager,
    tokenizer=self.tokenizer,
)
```

## 4. Tools & External Integrations

- **MCP servers (stdio/SSE/streamable-http)**: dynamically loads MCP tools/resources (`list_resources`, `read_resource`) and wraps them as callable tools (`envs/utils/mcp_manager.py:160-287`, `envs/tool_manager/qwen3_manager.py:200-215`).
- **Qwen-Agent tool ecosystem**: uses `TOOL_REGISTRY`, `BaseTool`, and function-call schema flow (`envs/tool_manager/qwen3_manager.py:14-15,195-227`).
- **Custom/native tool classes via YAML config**: tool classes are dynamically imported and initialized from config (`verl/tools/utils/tool_registry.py:81-107`).
- **External retrieval/search API**: `SearchTool` calls a configured retrieval HTTP service URL with rate limiting (`verl/tools/search_tool.py:175-180,218-224`).
- **Ray distributed runtime**: async server workers, loop workers, remote reward compute (`verl/experimental/agent_loop/agent_loop.py:203-544`, `verl/trainer/ppo/reward.py:162-179`).
- **Optional sandboxed reward scoring service**: reward manager can call sandbox fusion endpoint for scoring (`verl/trainer/ppo/reward.py:115-127`).
- **Dynamic Python tool code execution (config mode)**: compiles tool Python snippets via `exec` in `ConfigManager` (`envs/tool_manager/config_manager.py:122-138`).

## 5. Notable Code Walkthrough

- `verl/experimental/agent_loop/tool_agent_loop.py:31-167`  
  Core multi-turn tool-calling loop. Defines stop criteria, tool-call extraction, parallel tool execution, and response-mask bookkeeping used for RL trajectory construction.

- `verl/experimental/agent_loop/agent_loop.py:203-321`  
  Worker orchestration layer that maps each sample to an agent loop implementation (`single_turn_agent` or `tool_agent`) and runs them concurrently with Ray + asyncio.

- `envs/tool_manager/qwen3_manager.py:73-110,195-263`  
  Builds tool registry from MCP/native config, parses model outputs into tool actions, executes tool calls asynchronously, and returns tool-role messages back to the prompt pipeline.

- `envs/utils/mcp_manager.py:160-227,586-647`  
  MCP integration spine: initializes client sessions, auto-registers MCP tools/resources as callable tool classes, and executes calls with retry/reconnect logic.

- `verl/trainer/ppo/reward.py:84-138`  
  Reward manager loading logic (naive/prime/batch/dapo/custom), including custom reward function injection and optional sandbox-backed scoring for RL updates.

## 6. Use-Case Mapping

The assigned label **Simulation** is only partially accurate. The repo *does* “simulate” interactive trajectories (LLM outputs + tool observations), but its practical purpose is broader: **automating the RL post-training workflow for tool-using agents** (data -> rollout -> tool execution -> reward -> optimization). The strongest fit from the provided categories is **Workflow Automation**, because the main contribution is an automated training pipeline/orchestration framework, not a domain simulator environment alone (`README.md:13-17`, `envs/mmbase.py:143-210`, `verl/trainer/ppo/reward.py:84-138`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong decoupling of environment/tool wiring from RL trainer core (`README.md:45-52`, `envs/tool_manager/base_manager.py:11-39`).
  - Practical MCP integration (stdio/SSE/resource support) with retry/reconnect robustness (`envs/utils/mcp_manager.py:383-472,539-647`).
  - Async + parallel tool execution and Ray-based scaling are first-class (`envs/tool_manager/qwen3_manager.py:112-129`, `verl/experimental/agent_loop/agent_loop.py:486-513`).
  - Multiple tool backends (native tool classes + MCP + retrieval APIs) behind unified schemas (`verl/tools/utils/tool_registry.py:81-107`).

- **Limitations:**
  - Not true multi-agent coordination (no planner/manager-agent delegation at runtime); mostly one policy loop with tool feedback (`verl/experimental/agent_loop/tool_agent_loop.py:70-123`).
  - Some configuration paths execute arbitrary Python via `exec`, which is risky in untrusted settings (`envs/tool_manager/config_manager.py:132`).
  - Tool-call parsing relies on brittle textual tags/JSON fragments (`<tool_call>...</tool_call>`), which can fail under malformed outputs (`envs/tool_manager/qwen3_manager.py:297-367`).
  - Architecture complexity and mixed legacy/new paths (env tool managers vs experimental agent loops) may raise maintenance burden.

- **Research relevance:**
  - Useful evidence for **RL fine-tuning of tool-use policies** with multi-turn interaction traces.
  - Demonstrates **systems-level optimizations** (async tool calls, distributed rollout/reward workers) for agent training throughput.
  - Provides a real implementation of **MCP-enabled tool augmentation** inside RL training loops.
  - Suitable as a case study in bridging LLM function-calling protocols with policy optimization pipelines.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
