---
repo_name: cnoe-io/ai-platform-engineering
url: "https://github.com/cnoe-io/ai-platform-engineering"
stars: 347
forks: 55
contributors_count: 35
last_commit_date: "2026-04-22T18:32:04+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:29:30.096459+00:00"
model: auto
duration_s: 103.8
clone_size_kb: 129826
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`cnoe-io/ai-platform-engineering` is a production-oriented platform for running coordinated AI agents that execute DevOps/platform workflows (GitHub, AWS, ArgoCD, Jira, etc.) and optionally augment answers with a RAG knowledge base. A user typically interacts through the supervisor API/A2A stream, sends an operational request, and receives streamed execution-plan updates, tool notifications, and final results (including structured HITL forms when input is needed). The core runtime builds a multi-agent “platform engineer” supervisor that delegates tasks to specialized subagents and can run them in-process (MCP tools) or as remote A2A agents. The repo also includes a dynamic-agent runtime where agents/subagents are configured from MongoDB and composed at runtime. In practice, this solves “automate platform tasks with controlled agent orchestration + human checkpoints,” not just chat Q&A.

## 2. Agent Framework & Architecture

Frameworks used in actual code are **LangGraph + LangChain + deepagents + A2A SDK**, with MCP integration. This is explicit in dependency and imports (`pyproject.toml:21-34`, `ai_platform_engineering/multi_agents/platform_engineer/deep_agent.py:26-41`, `ai_platform_engineering/multi_agents/platform_engineer/protocol_bindings/a2a/agent_executor.py:12-33`). The upstream “CrewAI” label appears inaccurate for the core runtime.

The main architecture is a **supervisor deep-agent** that composes many domain subagents (GitHub, AWS, ArgoCD, Jira, Webex, etc.), utility tools, workflow tools, middleware, and optional RAG tools. The supervisor graph is built with `create_deep_agent(...)`, passing `subagents`, `tools`, policy/deterministic middleware, and persistence backends (`deep_agent.py:1589-1680`). Intelligence is split across: (a) generated system prompts + subagent prompts, (b) deterministic workflow middleware, and (c) model-driven tool/subagent routing.

Each domain agent can itself be LangGraph/deepagents-based (e.g., GitHub graph and AWS deep-agent). The platform also supports **distributed multi-agent mode** by wrapping remote agents as A2A tools (`deep_agent.py:1020-1053`, `ai_platform_engineering/utils/a2a_common/a2a_remote_agent_connect.py:44-93`), so orchestration can span multiple containers/services.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker with graph-based execution internals**.

- **Manager-worker:** the platform supervisor emits plans and delegates via `task`/subagent calls (`agent.py:1477-1505`), while subagents execute domain actions and stream artifacts back (`a2a_remote_agent_connect.py:373-423`).
- **Graph-based internals:** both supervisor and several agents are LangGraph/deepagents state machines (`deep_agent.py:1637-1667`, `agents/github/agent_github/graph.py:104-136`).

Control flow is explicit: supervisor builds plan (`write_todos`), routes to subagent tools, updates execution-plan artifacts, and synthesizes final output in A2A executor (`agent.py:1412-1475`, `agent_executor.py:693-745`).

## 4. Tools & External Integrations

- **MCP servers (primary tool surface):** supervisor/subagents load MCP tools via `MultiServerMCPClient` and per-agent loaders (`deep_agent.py:33, 704-713, 1239-1256`).
- **Remote A2A agents:** wrapped with `A2ARemoteAgentConnectTool`, including streaming relay and retries (`a2a_remote_agent_connect.py:44-53`, `186-270`, `343-423`).
- **RAG server + tools:** supervisor health-checks RAG server, loads MCP RAG tools, and wraps `search`/`fetch_document` with caps (`deep_agent.py:1395-1455`; wrappers in `rag_tools.py:109-166`, `171-233`).
- **RAG backend services:** vector DB query service, Redis, graph DB, FastMCP tool registration (`knowledge_bases/rag/server/src/server/tools.py:29-93`, `136-193`, `219-283`).
- **Workflow/self-service config store:** MongoDB/YAML-loaded task configs drive deterministic workflows (`deep_agent.py:395-425`, `461-560`).
- **Infra/CLI-style tools:** shared `curl/git/wget/grep/jq/yq/file` tools exposed to agents (`multi_agents/tools/__init__.py:27-41`; example `curl_tool.py:36-127`).
- **Persistence/checkpointing:** LangGraph checkpointer/store backends (memory, Redis/Postgres/Mongo) attached at runtime (`deep_agent.py:1668-1677`; deps in `pyproject.toml:38-48`).

## 5. Notable Code Walkthrough

- `ai_platform_engineering/multi_agents/platform_engineer/deep_agent.py:1107-1683`  
  Builds the core supervisor MAS: loads task configs, subagents, RAG tools, middleware, response format strategy, and checkpointer; this is the heart of orchestration.

- `ai_platform_engineering/multi_agents/platform_engineer/protocol_bindings/a2a/agent.py:483-689, 1412-1609`  
  Streams LangGraph events, handles HITL resume, emits execution-plan/tool artifacts, and converts model/tool activity into A2A-friendly event payloads.

- `ai_platform_engineering/multi_agents/platform_engineer/protocol_bindings/a2a/agent_executor.py:89-1469`  
  A2A executor that translates streamed events into protocol artifacts (`execution_plan_update`, `tool_notification_*`, `final_result`) and manages completion/input-required states.

- `ai_platform_engineering/utils/a2a_common/a2a_remote_agent_connect.py:44-147, 186-423`  
  Implements remote subagent delegation over A2A with retries/heartbeat/stream forwarding; enables distributed multi-agent deployments.

- `ai_platform_engineering/knowledge_bases/rag/server/src/server/tools.py:52-105, 126-249`  
  Registers/searches/fetches knowledge-base tools (including graph-RAG operations), showing concrete RAG plumbing that agents call.

## 6. Use-Case Mapping

This repo clearly implements **RAG + Agents**, but in this codebase RAG is a subsystem inside a broader **workflow-automation multi-agent platform**. The supervisor can load RAG tools and enforce search/fetch caps (`deep_agent.py:1442-1455`, `rag_tools.py:171-233`), so retrieval-augmented responses are real and runtime-integrated. At the same time, most architectural weight is on orchestrating operational tasks across external systems (GitHub/AWS/Jira/ArgoCD/Webex) with execution planning and deterministic workflow steps (`deep_agent.py:461-560`, `1589-1667`). So the assigned label is partially right, but the best top-level category is **Workflow Automation** with strong RAG support.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong real-world MAS orchestration with supervisor + many specialized subagents (`deep_agent.py:1082-1100`, `1262-1323`).
  - Robust streaming protocol design (plan/tool/final artifacts) for UX and observability (`agent_executor.py:693-745`, `746-856`).
  - Hybrid deployment model: local MCP tools and remote A2A agents in one orchestration layer (`deep_agent.py:1280-1292`, `1030-1053`).
  - Practical safety controls for RAG loops and context bloat (`rag_tools.py:76-103`, `147-166`, `209-233`).
  - HITL form interrupts and resume flow are integrated into runtime, not bolted on (`agent.py:710-729`, `723-727` in dynamic runtime resume path).

- **Limitations:**
  - Complexity is very high; orchestration logic is spread across large files (notably `agent.py`/`agent_executor.py`), raising maintenance risk.
  - Heavy prompt-engineering dependence for some agent behavior (e.g., large AWS prompt policy), which may be brittle across models (`agent_langgraph.py:85-260+`).
  - Many integrations depend on environment/config correctness (MCP/A2A endpoints, profiles, RAG server); failure modes are handled but operational burden is high.
  - Multiple modes (single-node, distributed, dynamic) create architectural surface area that may complicate reproducibility in research baselines.
  - Some subagent paths are marked as partial/stub-like (e.g., GitLab remote note) (`deep_agent.py:985-1013`).

- **Research relevance:**
  - Evidence of production-style **hierarchical MAS orchestration** with explicit planning artifacts and subagent delegation.
  - Useful case for studying **streaming protocol semantics** in multi-agent systems (tool events, plan updates, final synthesis).
  - Demonstrates **hybrid local+remote agent federation** (MCP + A2A) in one runtime.
  - Shows practical approaches to **RAG guardrails** (caps/truncation/hard-stop state) in agent loops.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
