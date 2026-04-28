---
repo_name: modelscope/ms-agent
url: "https://github.com/modelscope/ms-agent"
stars: 4188
forks: 491
contributors_count: 47
last_commit_date: "2026-04-15T06:21:35+00:00"
primary_use_case: Simulation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T13:31:05.703846+00:00"
model: auto
duration_s: 87.8
clone_size_kb: 93174
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`modelscope/ms-agent` is a lightweight Python framework for building LLM agents and configurable agent workflows from YAML. A user typically runs `ms-agent run --config <task-dir-or-yaml>` (or `--project <built-in-project>`) and gets an autonomous loop that can call tools, use memory/RAG, and optionally chain multiple agents. Under the hood, configs load prompts, models, callbacks, and tool servers, then execute either a single `LLMAgent` or a workflow (`ChainWorkflow`/`DagWorkflow`) (`ms_agent/cli/run.py:247-263`, `ms_agent/agent/llm_agent.py:1092-1208`). The output is usually a final assistant response plus artifacts on disk (reports, evidence, history), depending on project config (`projects/deep_research/v2/*.yaml`).

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework** (not LangGraph/CrewAI/AutoGen/LangChain orchestration). Core classes are custom: `Agent`, `LLMAgent`, `AgentLoader`, `WorkflowLoader`, `ChainWorkflow`, and `DagWorkflow` (`ms_agent/agent/base.py:12-80`, `ms_agent/agent/loader.py:15-74`, `ms_agent/workflow/loader.py:26-53`). I did not find runtime orchestration imports from LangGraph/CrewAI/AutoGen; only optional `llama_index` integration is used for RAG (`ms_agent/rag/llama_index_rag.py:42-56`).

Architecture is config-driven: YAML defines model/provider, prompt files, tools, callbacks, and optional external code handlers (`ms_agent/config/config.py:58-107`). `LLMAgent` contains the main “intelligence loop”: create messages, optional skill routing, optional RAG/knowledge search enrichment, LLM generation with tool schemas, tool execution, memory updates, and stop conditions (`ms_agent/agent/llm_agent.py:1123-1169`, `:839-969`).

Multi-agent behavior is implemented in two ways: (1) workflow-level composition (sequential or DAG of agent tasks) (`ms_agent/workflow/chain_workflow.py:59-113`, `ms_agent/workflow/dag_workflow.py:63-105`), and (2) **agent-as-tool delegation** where one agent invokes other full agents as tools (`ms_agent/tools/agent_tool.py:173-206`, `projects/deep_research/v2/researcher.yaml:62-134`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker**, with optional **DAG workflow orchestration**.

At runtime, a top-level agent can call sub-agents through `AgentTool` definitions (manager delegates to specialized workers), as seen in Deep Research v2 where `researcher` calls `searcher_tool` and `reporter_tool` (`projects/deep_research/v2/researcher.yaml:68-134`). Independently, the framework supports explicit sequential or DAG execution across agent tasks (`ms_agent/workflow/chain_workflow.py`, `ms_agent/workflow/dag_workflow.py`).

Short excerpts showing control flow:

```text
# ms_agent/workflow/chain_workflow.py:99-113
engine = AgentLoader.build(**init_args)
outputs = await engine.run(inputs)
next_idx = engine.next_flow(idx)
if next_idx == idx + 1:
    inputs = outputs
    agent_config = engine.config
else:
    inputs, agent_config = step_inputs[next_idx]
idx = next_idx
if idx >= len(self.workflow_chains):
    break
```

```text
# ms_agent/tools/agent_tool.py:83-89, 398-415
agent = AgentLoader.build(
    config_dir_or_id=spec.config_path, config=config_override, ...
)
...
response = await asyncio.wait_for(
    tool_ins.call_tool(server_name,
        tool_name=tool_name.split(self.TOOL_SPLITER)[1],
        tool_args=call_args),
    timeout=self.tool_call_timeout)
```

## 4. Tools & External Integrations

- **MCP servers/tools**: dynamic connection over stdio/SSE/websocket/streamable-http; tool discovery and invocation via MCP protocol (`ms_agent/tools/mcp_client.py:33-66`, `:143-246`, `:248-272`).
- **Web search engines**: built-in web search tool with engines including Exa and arXiv; optional content fetch/summarization in project configs (`ms_agent/tools/tool_manager.py:89-90`, `projects/deep_research/v2/searcher.yaml:37-56`, `ms_agent/tools/search/exa/search.py`, `ms_agent/tools/search/arxiv/search.py`).
- **Filesystem tooling**: local file read/write/list/search/replace operations exposed as tools (`ms_agent/tools/tool_manager.py:58-62`, `projects/deep_research/v2/researcher.yaml:31-39`).
- **Code execution**: sandboxed or local Python environment executor (`ms_agent/tools/tool_manager.py:62-77`, `ms_agent/tools/code/code_executor.py`, `ms_agent/tools/code/local_code_executor.py`).
- **Agent delegation (sub-agent calls)**: any configured agent can be exposed as a callable tool, including isolated subprocess execution (`ms_agent/tools/agent_tool.py:173-206`, `:593-677`).
- **RAG / vector retrieval**: optional LlamaIndex-backed retrieval, embedding setup, retrieval/query engine (`ms_agent/rag/llama_index_rag.py:13-56`, `:166-234`).
- **LLM providers**: OpenAI-compatible and other providers via service mapping (`ms_agent/llm/llm.py:72-77`, provider modules under `ms_agent/llm/`).
- **Domain integrations**: financial data sources (`ms_agent/tools/findata/*.py`), image/audio/video generation tools (`ms_agent/tools/image_generator/*`, `audio_generator/*`, `video_generator/*`).

## 5. Notable Code Walkthrough

- `ms_agent/agent/llm_agent.py:839-969,1092-1208` - Core agent runtime loop; interleaves LLM generation with tool calls, memory updates, callbacks, history persistence, and stop criteria.
- `ms_agent/tools/tool_manager.py:40-99,141-249` - Central tool wiring layer; merges MCP tools and built-ins/plugins, applies concurrency limits/timeouts, and executes parallel tool calls.
- `ms_agent/tools/agent_tool.py:173-339,522-710` - Key multi-agent primitive; turns configured agents into callable tools, runs them in thread/subprocess isolation, and streams results.
- `ms_agent/workflow/chain_workflow.py:17-57,75-113` - Sequential workflow executor; builds linear task order from config and passes outputs/config between agent steps.
- `projects/deep_research/v2/researcher.yaml:62-134` - Concrete MAS config; defines `searcher_tool` and `reporter_tool` sub-agents, demonstrating runtime manager-to-worker delegation.

## 6. Use-Case Mapping

The assigned primary use case (`Simulation`) looks **misclassified** based on code. The repository is primarily a **general agent orchestration/workflow automation framework**: it executes multi-step tasks by coordinating tools, data retrieval, and delegated sub-agents (`ms_agent/agent/llm_agent.py`, `ms_agent/tools/agent_tool.py`, `ms_agent/workflow/*`). Some bundled projects produce reports, code, or media pipelines, but the common core is automating complex workflows rather than simulating environments/agents. Better category: **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Strong config-first design makes agent behaviors reusable across projects (`ms_agent/config/config.py:58-107`).
- Supports both workflow-level and tool-level multi-agent composition (`ms_agent/workflow/*`, `ms_agent/tools/agent_tool.py`).
- Broad integration surface (MCP, web search, filesystem, code exec, RAG, provider abstraction).
- Practical runtime controls: tool timeouts, concurrency semaphores, retries, caching/history, callbacks (`ms_agent/tools/tool_manager.py:29-31,229-249`; `ms_agent/agent/llm_agent.py:839-969`).
- Subprocess isolation for delegated agents improves robustness for long/fragile sub-tasks (`ms_agent/tools/agent_tool.py:593-704`).

- **Limitations:**
- Orchestration is mostly imperative/config-driven; no explicit typed state graph or formal planner policy comparable to LangGraph.
- Reliability depends heavily on prompt/config quality; many controls are heuristic (round limits, self-reflection callbacks in project configs).
- Limited built-in global coordination semantics (shared blackboard/conflict resolution across many agents is project-specific, not framework-enforced).
- Security/trust model requires `trust_remote_code` for dynamic plugins/handlers, increasing supply-chain risk if misused (`ms_agent/agent/loader.py:79-83`, `tool_manager.py:104-109`).
- Test coverage appears component-heavy but end-to-end MAS benchmarking is not deeply embedded in core runtime.

- **Research relevance:**
- Good evidence of **practical hierarchical MAS** where LLM agents delegate to specialized LLM sub-agents at runtime.
- Useful case study for **tool-augmented agent engineering** with mixed local/MCP tool ecosystems.
- Demonstrates production-style concerns (timeouts, process isolation, caching/history, callback hooks) in multi-agent systems.
- Suitable for studying config-driven agent programmability vs. hardcoded orchestration.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
