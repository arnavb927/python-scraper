---
repo_name: Azure-Samples/python-agentframework-demos
url: "https://github.com/Azure-Samples/python-agentframework-demos"
stars: 230
forks: 151
contributors_count: 6
last_commit_date: "2026-04-06T18:36:39+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:42:28.697260+00:00"
model: auto
duration_s: 69.7
clone_size_kb: 74974
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a hands-on demo suite for the **Microsoft Agent Framework (Python)**, where users run individual scripts under `examples/` to try specific agent patterns (single-agent tools, supervisor/sub-agent delegation, multi-agent workflows, HITL, RAG, MCP, evaluation). In practice, a user executes commands like `uv run examples/workflow_handoffbuilder.py` or `uv run examples/agent_supervisor.py` and gets live LLM-driven outputs in terminal (optionally with streamed events or DevUI). The project solves the “how do I build production-style agent workflows in Python?” problem by giving many small, runnable references rather than one monolithic app. It also demonstrates how to switch model backends (Azure OpenAI or OpenAI), add tools, route between agents, and integrate storage/observability services.

## 2. Agent Framework & Architecture

The codebase is built around **Microsoft Agent Framework** (not CrewAI/LangGraph/AutoGen): imports consistently use `agent_framework` and related packages (`agent_framework.openai`, `agent_framework.orchestrations`) across runtime examples, and dependencies pin `agent-framework-*` packages in `pyproject.toml:22-29`. Agents are instantiated via `Agent(...)`, usually with `OpenAIChatClient`, instructions, and optional tools/context providers (e.g., `examples/agent_supervisor.py:80-88`, `examples/agent_knowledge_pg.py:320-329`).

Architecture is intentionally pattern-driven: each file demonstrates one orchestration primitive. “Intelligence” mainly lives in (a) per-agent role prompts/instructions, (b) workflow topology/routing conditions, and (c) tool/context wiring. For example, the same base `Agent` object can participate in sequential/concurrent/conditional/handoff/Magentic orchestrations (`examples/workflow_agents_concurrent.py:85-87`, `examples/workflow_conditional_structured.py:123-129`, `examples/workflow_handoffbuilder.py:114-125`, `examples/workflow_magenticone.py:92-99`).

Multi-agent coordination is explicit at runtime in several files: supervisor calling specialist agents as tools, concurrent multi-specialist fan-out, handoff-based agent transfer, and manager-led Magentic orchestration. So this is a true MAS demo repo, not just single-agent wrappers.

## 3. Orchestration Pattern

Closest overall match: **graph/workflow orchestration with multiple specialized sub-patterns** (sequential, concurrent, conditional, handoff, manager-worker). Control flow is encoded as workflow edges/builders and runtime handoff events rather than ad-hoc loops.

Example 1 (conditional graph routing):
```123:129:examples/workflow_conditional_structured.py
workflow = (
    WorkflowBuilder(start_executor=writer)
    .add_edge(writer, reviewer)
    .add_edge(reviewer, publisher, condition=is_approved)
    .add_edge(reviewer, editor, condition=needs_revision)
    .build()
)
```

Example 2 (autonomous handoff among agents):
```114:124:examples/workflow_handoffbuilder.py
workflow = (
    HandoffBuilder(
        name="content_pipeline",
        participants=[triage, researcher, writer, editor],
        termination_condition=lambda conversation: (
            len(conversation) > 0 and conversation[-1].text.strip().startswith("FINAL:")
        ),
    )
    .with_start_agent(triage)
    .with_autonomous_mode()
    .build()
)
```

This repo therefore is not a single fixed architecture; it is a catalog of orchestration patterns implemented through Agent Framework builders.

## 4. Tools & External Integrations

- **LLM providers (Azure OpenAI / OpenAI)**: wired through `OpenAIChatClient` and env-based host switch in most examples (`examples/agent_supervisor.py:23-39`, `examples/workflow_magenticone.py:26-42`).
- **MCP servers (remote + local)**: `MCPStreamableHTTPTool` connects agents to external MCP capabilities, including Microsoft Learn and local expense server (`examples/agent_mcp_remote.py:41-52`, `examples/agent_mcp_local.py:42-51`, `examples/workflow_handoffbuilder.py:54-57`).
- **Custom function tools**: `@tool` functions for weather, activities, meal planning, email ops, etc., including approval-gated tools (`examples/agent_supervisor.py:46-77`, `examples/workflow_hitl_tool_approval.py:59-115`).
- **Human-in-the-loop tool approval**: runtime approval loop processes `function_approval_request` events and resumes workflow with responses (`examples/workflow_hitl_tool_approval.py:193-214`).
- **RAG with PostgreSQL + pgvector + FTS**: hybrid retrieval and context injection via custom `ContextProvider` (`examples/agent_knowledge_pg.py:170-201`, `examples/agent_knowledge_pg.py:233-305`).
- **RAG ingestion pipeline (non-agent executors)**: file extraction via `markitdown` and embedding via OpenAI embeddings API (`examples/workflow_rag_ingest.py:62-77`, `examples/workflow_rag_ingest.py:94-110`).
- **Datastores**: PostgreSQL/pgvector directly in RAG file (`examples/agent_knowledge_pg.py:34`, `examples/agent_knowledge_pg.py:312-314`); README shows Redis/SQLite variants are also present in repo examples.
- **Telemetry/evaluation ecosystem**: package deps and examples include OpenTelemetry, Azure Monitor, and Azure AI Evaluation (`pyproject.toml:16-21`, README table entries at `README.md:208-213`).

## 5. Notable Code Walkthrough

- `examples/agent_supervisor.py:80-97,149-181` — Defines two specialist agents (weekend + meal), wraps each as a callable tool, then has a supervisor agent choose/delegate and synthesize. This is a clear manager-worker implementation using agent-as-tool composition.
- `examples/workflow_handoffbuilder.py:60-110,114-125,134-143` — Builds a triage/researcher/writer/editor pipeline with autonomous handoffs and stream-time handoff events; demonstrates dynamic control transfer instead of static single-pass sequencing.
- `examples/workflow_magenticone.py:80-99,131-163,196-201` — Uses `MagenticBuilder` with a manager agent and specialists; includes orchestration ledger event handling, making planner decisions observable during execution.
- `examples/workflow_conditional_structured.py:47-74,85-94,123-129` — Shows typed reviewer output (`response_format`) driving graph branch decisions through explicit conditions, a robust alternative to brittle string parsing.
- `examples/agent_knowledge_pg.py:233-305,320-329` — Implements custom hybrid search context provider (vector + keyword RRF) injected before LLM calls, illustrating retrieval-augmented agent behavior without explicit tool-calling by the model.

## 6. Use-Case Mapping

The assigned category **Browser / Terminal Use** appears **mostly inaccurate** for this repo’s core behavior. While scripts are run in terminal, agents are not primarily controlling a browser, shell, or desktop environment; instead they orchestrate LLM tasks, tools, routing, and HITL workflows. The dominant realized use case is **Workflow Automation** (with a secondary strong theme of **RAG + Agents** in dedicated examples like PostgreSQL/Azure AI Search). Recommended final category: **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad, runnable coverage of multi-agent orchestration modes in one repository.
  - Clear separation of concerns: role prompts, tool wiring, and graph control flow.
  - Practical HITL patterns (tool approval and request/response loops) for safer execution.
  - Strong integration examples (MCP, PostgreSQL hybrid RAG, Azure identity/model hosting).
  - Good educational value: small files isolate one concept per script.

- **Limitations:**
  - Mostly demo-grade scripts, not a unified production application architecture.
  - Many tools/data sources are mocked or toy-scale (e.g., static product catalog/email data).
  - Limited automated tests around orchestration correctness and failure handling.
  - Some examples are highly prompt-dependent; little formal policy/guardrail enforcement beyond HITL cases.
  - Cross-file reuse is low; repeated setup boilerplate may obscure reusable framework patterns.

- **Research relevance:**
  - Evidence of practical MAS orchestration patterns (manager-worker, handoff, concurrent specialists) in modern Python stacks.
  - Useful corpus for studying control-flow representations for LLM agents (edge conditions, typed routing, termination logic).
  - Demonstrates human-approval intervention points in agentic workflows.
  - Shows how retrieval/context providers can be composed with agent orchestration for grounded outputs.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
