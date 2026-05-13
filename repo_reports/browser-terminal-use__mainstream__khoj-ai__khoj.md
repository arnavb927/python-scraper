---
repo_name: khoj-ai/khoj
url: "https://github.com/khoj-ai/khoj"
stars: 34206
forks: 2164
contributors_count: 71
last_commit_date: "2026-03-26T03:33:47+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:26:38.011038+00:00"
model: auto
duration_s: 177.9
clone_size_kb: 154971
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`khoj-ai/khoj` is a self-hostable personal AI assistant platform that combines chat, retrieval over user documents, web research, code execution, and optional browser/computer operation. A user typically runs the server (often via Docker), opens the web app/API, and chats with either default behavior or explicit commands like `/research`, `/online`, `/code`, or `/operator`. Under the hood, it orchestrates LLM-driven planning plus tool execution across local and remote services, then synthesizes a final response. In practical terms, users get an “AI second brain” that can answer from notes, browse the web, run code in a sandbox, and perform longer multi-step research/automation tasks.

## 2. Agent Framework & Architecture

This repo uses a **custom orchestration framework**, not LangGraph/CrewAI/AutoGen/LlamaIndex as a runtime backbone. The code imports `langchain_core` types/prompts mostly for message/prompt utilities (`src/khoj/processor/conversation/prompts.py`, `src/khoj/processor/conversation/utils.py`), but the actual agent loop is hand-built around FastAPI routes and async generators (`src/khoj/routers/api_chat.py`, `src/khoj/routers/research.py`).

High-level architecture is split into at least two cooperating LLM roles: (1) a **planner/researcher** that chooses tool calls per iteration, and (2) a **response actor** that produces final user output from aggregated results. The planner is implemented in `apick_next_tool()` with a planning prompt and tool schema (`src/khoj/routers/research.py:277-474`), while execution occurs in `execute_tool()` plus special streaming handling for computer operation (`src/khoj/routers/research.py:64-275`, `564-707`). Final synthesis happens later in chat flow (`src/khoj/routers/api_chat.py:1380-1403`).

There is also a dedicated **operator agent subsystem** for computer/browser control (`src/khoj/processor/operator/__init__.py`). It instantiates model-specific operator agents (currently Anthropic path enabled), runs an iterative perceive-act loop over environment state, executes actions, and summarizes outcomes (`src/khoj/processor/operator/__init__.py:68-229`; `src/khoj/processor/operator/operator_agent_anthropic.py:52-223`).

## 3. Orchestration Pattern

Closest fit: **hierarchical manager-worker with iterative loop** (plus parallel tool fan-out).  
- Manager/planner: `apick_next_tool()` decides next tool call(s).  
- Workers: concrete tools (`search_documents`, `search_online`, `run_code`, MCP tools, operator).  
- Aggregator/synthesizer: research loop accumulates summarized iteration results, then chat generation uses that context.

Control-flow evidence (planner emits multiple calls, then parallel execution):

```537:646:src/khoj/routers/research.py
# Collect all tool calls from apick_next_tool
iterations_to_process: List[ResearchIteration] = []
...
# Execute parallelizable tools in parallel
tasks = [
    execute_tool(...)
    for iteration in parallel_iterations
]
tool_results = await asyncio.gather(*tasks, return_exceptions=True)
```

And the planning step that returns tool-call objects:

```438:471:src/khoj/routers/research.py
response_text = response.text
parsed_responses = [ToolCall(**item) for item in load_complex_json(response_text)]
...
for idx, parsed_response in enumerate(parsed_responses):
    yield ResearchIteration(
        query=parsed_response,
        warning=warning,
        raw_response=response.raw_content if idx == 0 else None,
    )
```

## 4. Tools & External Integrations

- **MCP servers/tools**: dynamic discovery and invocation of MCP tools via stdio or SSE (`src/khoj/processor/tools/mcp.py:13-125`), wired into research tool-choice and execution (`src/khoj/routers/research.py:376-391`, `253-264`, `500-503`).
- **Web search APIs**: Serper, Exa, Firecrawl, Google CSE, SearXNG (`src/khoj/processor/tools/online_search.py:101-117`, `187-439`).
- **Webpage scraping/extraction**: direct fetch + Firecrawl/Olostep/Exa fallback pipeline (`src/khoj/processor/tools/online_search.py:508-649`).
- **Code execution sandbox**: generated Python executed in E2B or Terrarium (`src/khoj/processor/tools/run_code.py:53-119`, `215-349`).
- **Browser/computer automation**: operator environments for Playwright browser and Docker-backed computer/terminal actions (`src/khoj/processor/operator/__init__.py:122-130`; `src/khoj/processor/operator/operator_agent_anthropic.py:598-635`; `src/khoj/processor/operator/operator_environment_browser.py` and `operator_environment_computer.py` referenced in `__init__.py`).
- **LLM providers**: OpenAI/Azure OpenAI, Anthropic, Gemini wrappers used across planning/chat/operator (`src/khoj/utils/helpers.py` client factories referenced by call-sites; e.g., `operator_agent_anthropic.py:417-439`, `grounding_agent.py:52-59`).
- **RAG/document retrieval**: semantic/document search tools invoked from research/chat (`src/khoj/routers/research.py:101-143`; `src/khoj/routers/api_chat.py:1081-1133`).

## 5. Notable Code Walkthrough

- `src/khoj/routers/research.py:64-707`  
  Core research orchestrator: picks next tools via LLM, executes streaming and non-streaming tools, parallelizes eligible calls, summarizes each iteration, and maintains loop state/cancellation.

- `src/khoj/routers/api_chat.py:992-1061, 1030-1048, 1384-1403`  
  Main chat pipeline: selects command/data-source mode, invokes research loop when needed, then generates final response from accumulated references/results.

- `src/khoj/processor/operator/__init__.py:34-229`  
  Operator runtime entrypoint: initializes model/environment, runs iterative action loop (state -> agent act -> env step -> feedback), handles interrupts, and yields trajectory/summary.

- `src/khoj/processor/operator/operator_agent_anthropic.py:52-223, 598-635`  
  Anthropic computer-use agent implementation: translates tool-use blocks into executable actions (mouse/keyboard/editor/terminal), then defines tool schemas/system instructions.

- `src/khoj/processor/tools/online_search.py:56-185, 508-570`  
  Online research worker: decomposes query into subqueries, runs multiple search backends, optionally reads pages, and extracts relevant snippets with LLM assistance.

## 6. Use-Case Mapping

Assigned label `Browser / Terminal Use` is **partially correct but not primary**. The repository does implement real browser/computer/terminal operation via the operator subsystem (`src/khoj/processor/operator/*`), including long-running iterative control loops and action execution. However, that is one mode among broader capabilities; the dominant architecture in chat and research is orchestrating multi-step information and action pipelines (RAG, web search, code execution, MCP tools, scheduling/automation). So the better primary category is **Workflow Automation** (with strong secondary `RAG + Agents` and optional `Browser / Terminal Use`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Clear production-grade async orchestration with cancellation, interrupts, and streaming status (`api_chat` + `research` loops).
- Flexible tool ecosystem: MCP, web search providers, webpage scrapers, code sandbox, operator environments.
- Parallel tool execution in research mode improves throughput for multi-query tasks (`asyncio.gather` in `research.py`).
- Strong separation between planner/tool-selection and execution workers, with iteration memory/summaries.
- Practical support for long tasks and resumable partial context (interrupted conversation/operator state handling).

- **Limitations:**
- Multi-agent semantics are mostly role-based in one service; not a decentralized/swarm architecture.
- Framework-level guarantees (typed graph/state machine à la LangGraph) are absent; orchestration logic is bespoke and complex.
- Operator model support is narrow in practice (Anthropic path enabled; other agent variants gated/TODO in code).
- Heavy prompt- and parsing-dependence may cause brittle behavior when model outputs drift (JSON/tool-call parsing fallbacks).
- Large router/helper modules concentrate many responsibilities, increasing maintenance complexity.

- **Research relevance:**
- Useful evidence of **applied hierarchical LLM orchestration** (planner -> parallel workers -> synthesizer) in a real product.
- Demonstrates integration of **LLM planning with heterogeneous tools** (MCP, web APIs, sandboxed code, browser/computer control).
- Shows pragmatic techniques for **agent robustness**: interruption handling, partial-state recovery, iterative summaries, tool dedupe checks.
- Illustrates hybrid “agentic RAG + automation” systems beyond toy benchmarks.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
