---
repo_name: PurpleAILAB/Decepticon
url: "https://github.com/PurpleAILAB/Decepticon"
stars: 2494
forks: 446
contributors_count: 5
last_commit_date: "2026-04-22T18:32:11+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-04-27T14:05:44.139843+00:00"
model: auto
duration_s: 108.1
clone_size_kb: 73498
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

Decepticon is an autonomous red-team operations system that runs a full engagement lifecycle rather than a single chat agent. In practice, users launch a LangGraph-served multi-agent stack (plus Docker sandbox and model proxy), then the system generates engagement docs (RoE/CONOPS/deconfliction), builds OPPLAN objectives, executes offensive tasks, and can trigger a defend-and-verify loop. The code shows objective-by-objective execution with state persisted to workspace files such as `plan/opplan.json`, `findings/FIND-*.md`, and `verification-*.json` (`decepticon/core/engagement_loop.py:60-220`). The output is not just text: it includes structured plans, findings artifacts, and knowledge-graph updates for later chaining and analysis (`decepticon/tools/research/tools.py:311-390`).

## 2. Agent Framework & Architecture

This repo is **LangChain + LangGraph + DeepAgents middleware**, not CrewAI. Agent construction uses `langchain.agents.create_agent`, middleware from `langchain` and `deepagents`, and graph routing via `langgraph.graph.StateGraph` (`decepticon/agents/decepticon.py:39-49`, `decepticon/agents/decepticon.py:317-327`). Each specialist agent module exposes a `graph = create_*_agent()` entrypoint used by `langgraph.json` (`langgraph.json:3-21`).

Architecture is multi-agent and role-specialized. The top orchestrator composes Soundwave (document/planning intake) and Decepticon (execution orchestrator), then Decepticon delegates to sub-agents like recon, exploit, analyst, reverser, cloud_hunter, ad_operator, postexploit via `SubAgentMiddleware` and `CompiledSubAgent` wrappers (`decepticon/agents/decepticon.py:156-269`, `decepticon/agents/decepticon.py:271-299`). Intelligence is distributed across: (a) role-specific system prompts loaded per agent, (b) middleware policy/state injection (especially OPPLAN), and (c) tool-rich specialist capabilities (`decepticon/agents/recon.py:81-138`, `decepticon/middleware/opplan.py:1170-1271`).

Model routing is centralized in `LLMFactory`, which instantiates `ChatOpenAI` clients pointed to a LiteLLM proxy with role-based primary/fallback models (`decepticon/llm/factory.py:30-126`).

## 3. Orchestration Pattern

Closest pattern: **hierarchical (manager-worker) with graph-based entry routing**.

- Graph routing picks Soundwave vs Decepticon based on engagement-doc existence (`decepticon/agents/decepticon.py:86-122`, `decepticon/agents/decepticon.py:317-327`).
- Inside Decepticon, manager-style delegation occurs through sub-agent tool calls (`SubAgentMiddleware`) to specialist workers (`decepticon/agents/decepticon.py:271-279`).
- A second sequential orchestrator loop exists in `EngagementLoop` for objective iteration and phase transitions ATTACK → VACCINE (`decepticon/core/engagement_loop.py:96-220`).

```317:325:decepticon/agents/decepticon.py
builder = StateGraph(OrchestratorState)
builder.add_node("check_docs", _check_engagement_docs)
builder.add_node("soundwave", soundwave)
builder.add_node("decepticon", decepticon)

builder.add_edge(START, "check_docs")
builder.add_conditional_edges("check_docs", _route_agent)
builder.add_edge("soundwave", END)
builder.add_edge("decepticon", END)
```

```144:159:decepticon/core/engagement_loop.py
agent_name = self._select_agent(obj)
prompt = self._build_attack_prompt(obj)

self._update_opplan_objective(obj.id, ObjectiveStatus.IN_PROGRESS)

response = await self._invoke_agent(agent_name, prompt)
result = self._parse_objective_result(response, obj, agent_name, start_time)
```

## 4. Tools & External Integrations

- **LLM gateway (LiteLLM/OpenAI-compatible)**: all agents call models through `ChatOpenAI(... base_url=proxy_url ...)` (`decepticon/llm/factory.py:117-126`).
- **LangGraph runtime API**: engagement loop invokes assistants over HTTP `/runs` with `assistant_id` (`decepticon/core/engagement_loop.py:519-558`).
- **Docker sandbox + terminal/tmux execution**: command execution and file ops happen in containerized sandbox, with persistent tmux sessions for interactive tooling (`decepticon/backends/docker_sandbox.py:579-739`, `decepticon/tools/bash/bash.py:155-247`).
- **Filesystem tooling via DeepAgents backend**: per-agent `FilesystemMiddleware` plus routed `CompositeBackend` (`decepticon/agents/recon.py:85-103`).
- **Knowledge graph backend (Neo4j with fallback state wrappers)**: graph CRUD and ingest tools, plus defense logging to KG (`decepticon/tools/research/tools.py:311-495`, `decepticon/tools/defense/tools.py:156-287`).
- **External security intel APIs**: NVD, OSV, EPSS via async HTTP lookups (`decepticon/tools/research/cve.py:44-47`, `decepticon/tools/research/cve.py:223-263`).
- **Security-data ingestion pipeline**: Nmap/Nuclei/Subfinder/httpx/dnsx/katana/masscan/ffuf/testssl parsers into KG (`decepticon/tools/research/tools.py:716-2243`).
- **Web-analysis helpers (not browser automation)**: JWT/OAuth/cookie/GraphQL analysis tools (`decepticon/tools/web/tools.py:25-155`).

No MCP server integration or browser automation framework wiring (e.g., Playwright) appears in runtime agent code.

## 5. Notable Code Walkthrough

- `decepticon/agents/decepticon.py:124-331` - Main orchestrator: builds middleware stack, registers specialist sub-agents, and compiles the LangGraph router that switches planning vs execution paths.
- `decepticon/core/engagement_loop.py:51-220` - Ralph-style system loop: iterates OPPLAN objectives, selects sub-agent per phase, parses outcomes, and transitions to vaccine/defense processing.
- `decepticon/middleware/opplan.py:378-1271` - Domain-specific planning middleware with objective CRUD, dependency/state-transition validation, and dynamic OPPLAN status injection into every model call.
- `decepticon/tools/bash/bash.py:155-247` - Terminal-use interface exposed to agents, including persistent sessions, background execution, output offloading, and sanitization.
- `decepticon/tools/research/tools.py:311-2392` - Massive research tool surface for KG operations, scanner ingestion, CVE enrichment, chain planning, fuzzing, and PoC validation.

## 6. Use-Case Mapping

This repo realizes **Browser / Terminal Use** primarily through terminal-centric autonomous operations: agents execute shell commands in persistent sandboxed tmux sessions, run offensive tooling, and consume artifacts from those runs (`decepticon/tools/bash/bash.py:164-213`, `decepticon/backends/docker_sandbox.py:690-714`). It also performs web-target analysis (JWT/OAuth/GraphQL/cookies), but via parsing/HTTP-tool workflows rather than full browser automation (`decepticon/tools/web/tools.py:84-155`).

That said, the dominant system behavior is end-to-end **workflow orchestration** of a red-team lifecycle (planning, objective tracking, delegation, verification, persistence) (`decepticon/middleware/opplan.py:74-137`, `decepticon/core/engagement_loop.py:60-120`). So the assigned label is partly right on terminal interaction, but the stronger top-level category is Workflow Automation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent decomposition with explicit orchestration and specialist delegation (`decepticon/agents/decepticon.py:156-299`).
  - Strong operational state model (OPPLAN objectives + transitions + dependency checks) rather than ad-hoc prompts (`decepticon/middleware/opplan.py:625-807`).
  - Practical long-horizon execution support via fresh-context iterations and filesystem/KG persistence (`decepticon/core/engagement_loop.py:128-139`, `decepticon/tools/research/tools.py:311-390`).
  - Realistic terminal automation with interactive session handling and safeguards (`decepticon/backends/docker_sandbox.py:206-339`).
  - Broad tooling breadth for recon, vuln research, and defense verification in one stack (`decepticon/tools/research/tools.py:2356-2392`, `decepticon/tools/defense/tools.py:63-154`).

- **Limitations:**
  - Heavy coupling to Docker + local infra + LangGraph API availability; failures degrade behavior significantly (`decepticon/core/engagement_loop.py:547-558`).
  - Security-sensitive automation uses heuristic parsing/signals in places (e.g., finding parsing, objective result token matching), which may be brittle (`decepticon/core/engagement_loop.py:669-687`).
  - No true browser automation path despite web focus; interaction is mostly shell/HTTP artifact driven.
  - Very large tool surface increases policy/control complexity and potential misuse risk.
  - Defense loop appears partially file-contract-based and external-process dependent (`decepticon/orchestrator.py:141-168`).

- **Research relevance:**
  - Good evidence of **hierarchical MAS orchestration** combining graph routing and manager-worker delegation.
  - Useful case for studying **stateful middleware governance** (task/objective constraints injected into LLM calls).
  - Demonstrates **agent memory via externalized state** (workspace files + KG) rather than long chat context.
  - Relevant for evaluating autonomous cyber-operation pipelines with offensive/defensive closed loops.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
