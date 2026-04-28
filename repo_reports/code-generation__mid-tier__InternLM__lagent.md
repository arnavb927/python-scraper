---
repo_name: InternLM/lagent
url: "https://github.com/InternLM/lagent"
stars: 2242
forks: 227
contributors_count: 34
last_commit_date: "2026-04-20T07:14:00+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 6
architecture_labels: [LangGraph, LangChain, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T12:40:36.465339+00:00"
model: auto
duration_s: 95.6
clone_size_kb: 911
uses_mas: yes
final_use_case: Workflow Automation
---
I now have enough code-level evidence to write the full report: confirmed this is a custom agent framework (not LangGraph/LangChain), with loop-based tool-using agents plus a true two-agent coordinator (`select_agent` + `env_agent`) and broad tool/API integrations. I’ll synthesize this into the exact requested section format next.## 1. Overview

`lagent` is a lightweight Python framework for building LLM-driven agents that can call tools, maintain memory, and run iterative reasoning-action loops. In practice, users instantiate an agent class (e.g., `ReAct`, `AgentForInternLM`, `FunctionCallAgent`), register actions/tools, and call it with a query; the framework handles prompt assembly, model invocation, tool dispatch, and memory updates. The output is typically an `AgentMessage` containing either final text or structured tool-call state plus tool results. It is more of an agent runtime library than a single application: you run example scripts or embed these classes into your own service. The core problem it solves is operationalizing LLM tool-use workflows with reusable abstractions (agent, action executor, parser, aggregator, memory).

## 2. Agent Framework & Architecture

This repo uses a **custom framework** (not LangGraph/LangChain/AutoGen/CrewAI at runtime). Core abstractions are implemented directly in `lagent/agents`, `lagent/actions`, `lagent/prompts/parsers`, and `lagent/memory`; import scans show no runtime dependency on those agent frameworks (only a comment reference in search-tool docs).

Architecture is modular:
- **Agent layer**: `Agent` encapsulates LLM calls + memory + prompt aggregation (`lagent/agents/agent.py:18-113`).
- **Orchestration layer**: higher-level agents implement iterative control (`ReAct`, `AgentForInternLM`, `FunctionCallAgent`) and call executors (`lagent/agents/react.py:28-65`, `lagent/agents/stream.py:56-113`, `lagent/agents/fc_agent.py:63-100`).
- **Tool layer**: `ActionExecutor` maps model-selected tool names to concrete `BaseAction` methods (`lagent/actions/action_executor.py:12-95`).
- **Prompt/IO layer**: parser+aggregator components encode/decode tool-call syntax and transform conversation history into model messages (`lagent/prompts/parsers/tool_parser.py:24-130`, `lagent/agents/aggregator/tool_aggregator.py:22-106`).

“Intelligence” lives primarily in model prompts/parsers and loop logic: the LLM selects actions, parsers extract action payloads, then executors run tools and feed environment outputs back into the next turn.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker loop** (with sequential loop behavior), plus optional agent containers.  
Reason: a selector/planner agent chooses tool actions, and an environment/executor agent performs them, then returns observations to continue/terminate (`lagent/agents/fc_agent.py:63-100`, `102-165`).

Excerpt 1 (`FunctionCallAgent` control loop):
```78:99:lagent/agents/fc_agent.py
async def forward(self, env_message: AgentMessage, session_id: str | int, **kwargs):
    selection_message: AgentMessage = None
    current_turn = 0
    while (self.finish_condition is None or not self.finish_condition(selection_message, env_message)) and (
        self.max_turn is None or current_turn < self.max_turn
    ):
        selection_message = await self.select_agent(env_message, session_id=session_id, **kwargs)
        ...
        env_message = await self.env_agent(selection_message, session_id=session_id)
        current_turn += 1
```

Excerpt 2 (`EnvAgent` executes selected tools, possibly parallel):
```127:144:lagent/agents/fc_agent.py
async def forward(self, selection_message: AgentMessage, session_id: str | int, **kwargs):
    if not selection_message.tool_calls:
        return AgentMessage(sender=self.name, content='No tool call')

    tool_responses = await asyncio.gather(
        *[
            self._retry_mechanism(self.execute_tool)(tool_call, session_id)
            for tool_call in selection_message.tool_calls
        ]
    )
    ...
    return AgentMessage(sender=self.name, content=[asdict(resp) for resp in tool_responses])
```

There is also a generic `Sequential` container for chaining multiple agents in order (`lagent/agents/agent.py:409-443`).

## 4. Tools & External Integrations

- **LLM providers/runtimes**: OpenAI, Anthropic, LMDeploy, vLLM, HuggingFace, SenseNova (`lagent/llms/__init__.py:1-40`).
- **Tool execution framework**: `BaseAction` + `tool_api` auto-schema generation + `ActionExecutor` dispatch (`lagent/actions/base_action.py:27-275`, `lagent/actions/action_executor.py:12-95`).
- **Python/code execution tools**: `PythonInterpreter`, `IPythonInterpreter`, `IPythonInteractive` (stateful notebook-like execution) (`lagent/actions/python_interpreter.py:33-135`, exported in `lagent/actions/__init__.py:8-14`).
- **Web/search integrations**: DuckDuckGo, Bing Search API, Serper/Google, Brave, Tencent Search, plus page fetch/parse with `requests`/`aiohttp`/BeautifulSoup (`lagent/actions/web_browser.py:50-206`, `451-583`, `784-981`).
- **Academic/search tools**: arXiv and Google Scholar actions are shipped (`lagent/actions/__init__.py:2-7`).
- **Map/geospatial integration**: Bing Map action (`lagent/actions/__init__.py:4`).
- **MCP integration**: `AsyncMCPClient` wraps one MCP tool, supports `stdio`/`sse`/`http` transports (`lagent/actions/mcp_client.py:225-410`).
- **Service deployment**: HTTP agent server/client wrappers for remote inference (`lagent/distributed/http_serve/api_server.py:14-131`) and Ray Serve modules in `lagent/distributed/ray_serve`.
- **No vector DB / classic RAG backend wiring** observed in core runtime (no Chroma/Pinecone/pgvector code paths found).

## 5. Notable Code Walkthrough

- `lagent/agents/agent.py:18-113,409-443` - Defines base `Agent` call lifecycle (hooks, memory, aggregation, LLM call) and `Sequential` composition; this is the framework’s central runtime contract.
- `lagent/agents/fc_agent.py:63-165` - Implements explicit two-agent orchestration (`select_agent` + `env_agent`), including stop conditions, error handling, and parallel tool execution with retries.
- `lagent/agents/stream.py:56-113,169-225` - Implements InternLM-oriented tool-use agents (`AgentForInternLM`/async variant) that loop over model output, parse tool directives, execute plugin/interpreter tools, and feed observations back.
- `lagent/actions/base_action.py:27-275,343-375` - Core action abstraction; automatically derives tool schemas from signatures/docstrings and normalizes execution/output into `ActionReturn`.
- `lagent/actions/web_browser.py:817-981` - Representative external-tool implementation combining multi-provider search + content retrieval APIs into callable tool methods (`search`, `select`, `open_url`).

## 6. Use-Case Mapping

The assigned use case (**Code Generation**) is only partially accurate. The framework can support code-centric tasks (notably via `PythonInterpreter`/`IPython*` tools and `MathCoder` in `lagent/agents/stream.py:130-167`), but the broader design is a **general tool-using agent orchestration runtime** for heterogeneous workflows (search, browsing, maps, MCP, presentation generation, remote serving).  

A better top-level category is **Workflow Automation**: the primary pattern is iterative planning + tool invocation + environment feedback loops across many non-code tools (`lagent/agents/react.py:59-65`, `lagent/agents/fc_agent.py:78-99`, `lagent/actions/action_executor.py:81-95`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clean separation of concerns (agent orchestration vs parsing vs tool execution vs memory).
  - Multiple orchestration styles supported (ReAct loop, selector-env two-agent loop, sequential composition).
  - Strong tool abstraction (`tool_api` metadata extraction + executor dispatch) eases adding new actions.
  - Broad integration surface (LLM backends, MCP, web/search APIs, interpreter tools, HTTP/Ray serving).
  - Async-first support in key paths (`AsyncAgent`, `AsyncActionExecutor`, async tool calls).

- **Limitations:**
  - Inconsistent/stale test references (e.g., test imports `lagent.agents.rewoo`, absent in current tree: `tests/test_agents/test_rewoo.py:6`).
  - Relies heavily on prompt/parser format correctness; malformed model output can break loops despite parsing safeguards.
  - Security/sandbox concerns for code-execution tools (`exec`/`eval` in `python_interpreter.py`) if used in untrusted contexts.
  - No built-in graph-state orchestration/visual tracing comparable to dedicated graph frameworks.
  - RAG infrastructure (retriever/vector-store pipelines) is not first-class in core code.

- **Research relevance:**
  - Useful evidence of **practical tool-augmented LLM agent engineering** in a lightweight custom stack.
  - Demonstrates a concrete **manager-environment multi-agent loop** with retry/concurrency control.
  - Shows how parser-constrained action formats and memory aggregation mediate agent reliability.
  - Illustrates real-world integration of MCP and heterogeneous web APIs inside an LLM-agent runtime.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
