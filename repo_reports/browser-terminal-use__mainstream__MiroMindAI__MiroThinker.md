---
repo_name: MiroMindAI/MiroThinker
url: "https://github.com/MiroMindAI/MiroThinker"
stars: 8108
forks: 610
contributors_count: 12
last_commit_date: "2026-01-28T05:27:56+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T11:19:31.964531+00:00"
model: auto
duration_s: 83.5
clone_size_kb: 22933
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

MiroThinker is a research-task agent runner (`apps/miroflow-agent/main.py`) that executes multi-turn LLM reasoning loops with MCP-style tools (search, scraping, code execution, VQA, transcription, reasoning). A user typically runs `uv run python main.py ...` with a Hydra config selecting model/provider and agent profile, then receives a final summarized answer (with boxed output) plus detailed logs in `logs/` (`apps/miroflow-agent/README.md:19-54`, `src/core/pipeline.py:35-143`). The system is built for benchmark-style “deep search” tasks where the model must iteratively collect evidence via tools, not just answer from parametric memory. It supports both current single-agent configurations and legacy multi-agent manager/sub-agent mode.

## 2. Agent Framework & Architecture

This is a **custom agent framework**, not LangGraph/CrewAI/AutoGen/LlamaIndex. The core loop is hand-rolled in `Orchestrator` (`apps/miroflow-agent/src/core/orchestrator.py:86-1203`) with custom LLM clients (`src/llm/*`) and a custom MCP `ToolManager` (`libs/miroflow-tools/src/miroflow_tools/manager.py:48-382`). Tool use is represented either as XML-tagged MCP calls or OpenAI-style tool calls, parsed by repo code (`src/utils/parsing_utils.py:311-433`).

Architecture is: pipeline bootstraps tool managers + LLM client, then orchestrator runs the main agent loop (`src/core/pipeline.py:180-217`, `src/core/pipeline.py:95-124`). “Intelligence” is primarily in prompt templates and iterative execution logic: system prompt generation with tool schemas, agent-specific role prompts, and strict summarization/final-answer prompting (`src/utils/prompt_utils.py:85-299`).

There are two runtime shapes:
- **Single-agent deep-research mode** (current MiroThinker v1.5 configs): main agent directly calls search/scrape/python tools (`conf/agent/mirothinker_v1.5.yaml:8-21`).
- **Hierarchical multi-agent mode** (legacy/default configs): main agent can invoke `agent-browsing` as a tool, and that sub-agent runs its own tool loop (`src/config/settings.py:383-419`, `src/core/orchestrator.py:923-969`, `conf/agent/multi_agent.yaml:17-24`).

## 3. Orchestration Pattern

Closest pattern: **hierarchical manager-worker** (with sequential ReAct-like loops inside each agent).

Main-agent control flow delegates to sub-agent when the selected server is `agent-*`:
`apps/miroflow-agent/src/core/orchestrator.py:923-955`
```python
if server_name.startswith("agent-") and self.cfg.agent.sub_agents:
    ...
    sub_agent_result = await self.run_sub_agent(
        server_name,
        arguments["subtask"],
    )
```

Sub-agent is exposed as a callable “tool” to main agent:
`apps/miroflow-agent/src/config/settings.py:399-416`
```python
name="agent-browsing",
tools=[
    dict(
        name="search_and_browse",
        description="This tool is an agent ...",
        schema={...}
    )
]
```

So control is manager -> (optional) worker sub-agent -> worker tool calls -> return summary -> manager continues. This is not a graph state machine (no node-edge runtime graph object), and not peer swarm.

## 4. Tools & External Integrations

- **MCP tool protocol + subprocess/SSE servers**: tool definitions and execution go through MCP client sessions (`libs/miroflow-tools/src/miroflow_tools/manager.py:104-195`, `:197-325`).
- **Web search APIs**:
  - Serper/Google search (`searching_google_mcp_server.py:84-163`, wired in `src/config/settings.py:88-115`).
  - Tencent Cloud Sogou search (`dev_mcp_servers/search_and_scrape_webpage.py:226-325`, wired in `src/config/settings.py:116-137` and `:288-309`).
- **Web scraping**:
  - Jina Reader scraping (`searching_google_mcp_server.py:648-713`, env wiring in `src/config/settings.py:29-31` and `:324-332`).
- **Python + shell execution sandbox**:
  - E2B sandbox tools (`python_mcp_server.py:89-170` for sandbox/commands, `:172-227` for Python execution), wired via `src/config/settings.py:139-149`.
- **LLM providers**:
  - OpenAI-compatible APIs (`openai_client.py:33-47`, factory `src/llm/factory.py:52-58`).
  - Anthropic (`src/llm/factory.py:53-55`; plus reasoning tool using Anthropic API in `src/config/settings.py:219-238`).
- **Multimodal tools**:
  - VQA server wiring (`src/config/settings.py:151-180`).
  - Audio transcription wiring (`src/config/settings.py:182-217`).
- **Document/file reading**:
  - `markitdown_mcp` and custom reading server (`src/config/settings.py:262-286`).
- **Optional Playwright session support** exists in `ToolManager` (`manager.py:228-241`) and `browser_session.py:16-60`, but default shipped agent configs in this repo primarily use search/scrape rather than browser action primitives.

## 5. Notable Code Walkthrough

- `apps/miroflow-agent/src/core/orchestrator.py:736-1203` - Main runtime loop: LLM call, tool-call parsing, duplicate-query rollback, optional sub-agent delegation, and final summarization.
- `apps/miroflow-agent/src/config/settings.py:68-380` - Central wiring layer mapping agent tool names to concrete MCP servers/env vars; this is where capabilities are actually enabled.
- `libs/miroflow-tools/src/miroflow_tools/manager.py:104-195` - Discovers tools from each MCP server and builds the tool schema list shown to the model.
- `apps/miroflow-agent/src/utils/prompt_utils.py:85-164` and `:204-299` - Generates system prompts/tool instructions and role-specific objectives for `main` vs `agent-browsing`.
- `libs/miroflow-tools/src/miroflow_tools/mcp_servers/python_mcp_server.py:89-227` - High-impact execution backend for terminal-like command and Python execution in isolated sandboxes.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate. The repo does include terminal-like execution via E2B (`run_command`, `run_python_code`) and optional browser-session support, but the dominant shipped workflow (especially `mirothinker_v1.5`) is **automated research orchestration** over search/scrape/python tools, producing final benchmark answers (`conf/agent/mirothinker_v1.5.yaml:8-21`).  
A better primary category is **Workflow Automation** (LLM orchestrates multi-step tool workflow to complete research tasks), with secondary overlap with Browser/Terminal Use.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear manager/sub-agent orchestration path with reusable sub-agent-as-tool abstraction (`src/config/settings.py:383-419`).
  - Strong operational safeguards: rollback on malformed tool format/refusals/duplicate queries (`src/core/orchestrator.py:180-317`).
  - Broad, practical tool stack (search, scraping, Python, VQA, audio, reader) wired through one protocol (`src/config/settings.py:68-380`).
  - Explicit context/answer recovery logic (failure summaries, retries, boxed-answer extraction) useful for long-horizon tasks (`src/core/answer_generator.py:170-591`).

- **Limitations:**
  - No explicit declarative workflow graph; control logic is large imperative loops, which can be harder to verify/extend (`src/core/orchestrator.py`).
  - Multi-agent mode appears legacy while flagship configs are mostly single-agent, so true MAS usage may be config-dependent (`apps/miroflow-agent/README.md:84-88`).
  - Tool-call interface relies on model-generated XML tags in many paths, creating fragility despite mitigations (`src/utils/parsing_utils.py:406-433`).
  - Heavy dependence on many external API keys/services reduces reproducibility out of the box (`src/config/settings.py:24-66`).

- **Research relevance:**
  - Evidence of a production-oriented **hierarchical LLM agent** pattern (manager delegates subtasks to specialized worker).
  - Good case study of **tool-augmented agent reliability engineering** (rollback, retry, duplicate suppression, context compression).
  - Demonstrates integration of MCP-like modular tool servers for extensible agent capabilities.
  - Useful benchmark-oriented architecture for studying long-horizon web research agents.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
