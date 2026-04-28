---
repo_name: confident-ai/deepeval
url: "https://github.com/confident-ai/deepeval"
stars: 14937
forks: 1377
contributors_count: 279
last_commit_date: "2026-04-22T07:52:51+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 8
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T09:42:23.915072+00:00"
model: auto
duration_s: 87.7
clone_size_kb: 50707
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`deepeval` is an LLM evaluation and tracing framework: users run `evaluate(...)`/`assert_test(...)` (or pytest-integrated flows) on test cases and metrics, and get structured pass/fail results plus optional upload to Confident AI (`deepeval/evaluate/evaluate.py:158-314`). In agentic settings, it does not primarily *run* agents itself; it instruments external runtimes (LangChain, LlamaIndex, CrewAI, OpenAI Agents), captures traces/spans, and then scores those traces with metrics (`deepeval/tracing/tracing.py`, `deepeval/integrations/*`). The practical output is metric scores, reasons, and trace-level diagnostics across LLM/tool/retriever/agent spans. So the repository solves “how do I evaluate and observe LLM/agent workflows consistently,” rather than “how do I build a new multi-agent runtime.”

## 2. Agent Framework & Architecture

Actual frameworks used in code are **custom tracing/evaluation core** plus **instrumentation adapters** for external ecosystems:
- LangChain (`deepeval/integrations/langchain/callback.py:40-57`)
- LlamaIndex (`deepeval/integrations/llama_index/handler.py:31-57`)
- CrewAI (`deepeval/integrations/crewai/handler.py:18-33`)
- OpenAI Agents SDK (`deepeval/openai_agents/callback_handler.py:20-38`)

No LangGraph runtime is implemented internally (LangGraph appears as a target of LangChain callback compatibility, not as a native graph engine). The core “intelligence” in this repo is metric prompting/scoring and trace traversal (e.g., task completion, MCP/tool correctness), not planner/worker agent logic (`deepeval/metrics/task_completion/task_completion.py:149-221`, `deepeval/metrics/mcp/multi_turn_mcp_use_metric.py:184-337`).

Architecture is: instrument app execution into a `Trace` of typed spans (`AgentSpan`, `LlmSpan`, `ToolSpan`, `RetrieverSpan`) via `Observer`/callbacks, then run evaluation over that trace (depth-first traversal, metric execution, aggregation) (`deepeval/tracing/tracing.py:932-1187`, `deepeval/evaluate/execute/agentic.py:74-190`). This is evaluator-centric rather than autonomous-agent-centric.

## 3. Orchestration Pattern

Closest match: **other (evaluation pipeline over traced execution DAG/tree)**, with a **mostly sequential + DFS traversal** for scoring.  
The system orchestrates **trace collection first**, then **metric execution across trace/span nodes**.

Control flow evidence:

```845:865:deepeval/evaluate/execute/loop.py
if not _has_any_evaluable_metrics(...):
    _raise_no_metrics_error()

# Evaluate traces
if trace_manager.eval_session.traces_to_evaluate:
    loop.run_until_complete(
        _a_evaluate_traces(...)
    )
```

```152:180:deepeval/evaluate/execute/agentic.py
async def dfs(trace: Trace, span: BaseSpan):
    await _a_execute_span_test_case(...)
    if _skip_metrics_for_error(span=span, trace=trace):
        return
    child_tasks = [asyncio.create_task(dfs(trace, child)) for child in span.children]
    if child_tasks:
        await asyncio.wait_for(asyncio.gather(*child_tasks), timeout=get_gather_timeout())
```

So orchestration is not manager-worker agent negotiation; it is runtime trace ingestion + hierarchical metric evaluation.

## 4. Tools & External Integrations

- **LLM providers (OpenAI, Anthropic) for tracing/metadata extraction**: client patching captures model, tokens, IO (`deepeval/tracing/patchers.py:16-124`, `125-221`).
- **Confident AI API backend**: traces/evaluations uploaded via HTTP (`deepeval/tracing/tracing.py:499-607`, `deepeval/evaluate/evaluate.py:283-314`).
- **LangChain integration**: callback handler maps chain/LLM/tool/retriever events into Deepeval spans (`deepeval/integrations/langchain/callback.py:70-849`).
- **LlamaIndex integration**: dispatcher event/span handlers for workflows, tool calls, LLM chat events (`deepeval/integrations/llama_index/handler.py:67-404`).
- **CrewAI integration**: event listener + method wrappers around kickoff/agent/tool events (`deepeval/integrations/crewai/handler.py:86-475`, `deepeval/integrations/crewai/wrapper.py:9-176`).
- **OpenAI Agents SDK integration**: tracing processor + span-data extractors for handoffs/tools/LLM generations (`deepeval/openai_agents/callback_handler.py:50-152`, `deepeval/openai_agents/extractors.py:56-260`).
- **MCP-aware evaluation (not MCP server runtime)**: metrics inspect conversational turns with MCP tools/resources/prompts usage (`deepeval/metrics/mcp/multi_turn_mcp_use_metric.py:22-377`).

No built-in browser automation, shell-agent runtime, or vector DB orchestration is wired as a native agent execution engine in core code.

## 5. Notable Code Walkthrough

- `deepeval/tracing/tracing.py:159-333, 932-1417` - Core trace manager and `@observe` mechanism; builds span trees (`agent/llm/tool/retriever`) and controls trace lifecycle.
- `deepeval/evaluate/execute/loop.py:497-1019` - Async evaluation loop; captures app callbacks, maps traces to goldens, then schedules trace-level evaluation with concurrency controls/timeouts.
- `deepeval/evaluate/execute/agentic.py:74-190, 302-512` - Agentic trace evaluator; executes metrics on trace and each span via DFS, handling `requires_trace` metrics and API result construction.
- `deepeval/integrations/langchain/callback.py:220-335, 394-520, 684-759` - Concrete adapter translating LangChain callback events into Deepeval spans and tool-call artifacts.
- `deepeval/integrations/llama_index/handler.py:181-283, 301-373` - LlamaIndex instrumentation mapping workflow/tool/LLM events to spans and trace completion semantics.

## 6. Use-Case Mapping

Assigned label `RAG + Agents` is only **partially** accurate. The repo clearly supports evaluating RAG/agent applications (retriever spans, tool calls, agent spans, MCP-aware metrics), but its primary function is **evaluation workflow orchestration** rather than running a native RAG multi-agent system. In practice, users bring their own LangChain/LlamaIndex/CrewAI/OpenAI Agents app, then Deepeval traces and scores it. A better top-level category is **Workflow Automation** (evaluation and observability pipeline for LLM/agent apps), with strong secondary relevance to RAG/agent assessment.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong cross-framework instrumentation coverage (LangChain, LlamaIndex, CrewAI, OpenAI Agents).
  - Unified typed trace model (`AgentSpan`/`LlmSpan`/`ToolSpan`/`RetrieverSpan`) enabling comparable evaluation across stacks.
  - Robust async handling (timeouts, task binding, stray-task cleanup) in evaluation loops.
  - Rich metric ecosystem, including trace-aware metrics (`requires_trace`) and MCP/tool-use evaluation.
  - Clear separation between runtime instrumentation and scoring pipeline.

- **Limitations:**
  - Not a native multi-agent execution framework; depends on external agent runtimes.
  - Complex callback/contextvar synchronization logic may be brittle across framework version drift.
  - “Agentic” quality depends on LLM-based meta-evaluation prompts, which can introduce evaluator model bias.
  - Integration-heavy architecture increases maintenance burden when upstream SDK event schemas change.
  - Limited direct support for reproducible agent-policy experiments (focus is eval, not controlled agent simulation).

- **Research relevance:**
  - Useful evidence for **agent observability/evaluation infrastructure** design in production.
  - Demonstrates practical **trace-based hierarchical evaluation** of tool-using LLM workflows.
  - Supports comparative studies of agent framework behavior via normalized span schema.
  - Relevant for studying metric design for MCP/tool correctness and task completion in conversational agents.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
