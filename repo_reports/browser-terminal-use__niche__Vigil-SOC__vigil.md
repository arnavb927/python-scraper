---
repo_name: Vigil-SOC/vigil
url: "https://github.com/Vigil-SOC/vigil"
stars: 133
forks: 25
contributors_count: 9
last_commit_date: "2026-04-23T05:38:20+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:56:23.165289+00:00"
model: auto
duration_s: 90.1
clone_size_kb: 7540
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

Vigil is an AI-native SOC platform that users run as a backend API plus frontend dashboard (and optionally a background daemon) to triage alerts, investigate incidents, and trigger response workflows. In practice, users can chat with role-specific SOC agents, launch autonomous investigations, and have the system coordinate tool calls across security integrations. The code shows two runtime modes: interactive chat/agent-task endpoints (`backend/api/claude.py`) and a continuously running autonomous orchestrator (`daemon/orchestrator.py`) that creates and supervises investigations. Outputs include investigation workdirs (`plan.md`, `context.md`, `review.md`), case updates, approval requests, and structured AI decision logs. The core value is automating SOC workflows end-to-end rather than offering only a single chatbot.

## 2. Agent Framework & Architecture

This repo is primarily a **custom multi-agent architecture** built on Anthropic APIs, with optional **Claude Agent SDK** integration. It does **not** use LangGraph/LangChain/CrewAI/AutoGen as a primary runtime framework based on imports and control flow; the key imports are Anthropic clients and `claude_agent_sdk` (`services/claude_service.py:80-83`, `services/claude_service.py:96-103`, `services/claude_service.py:3644-3703`).

Agents are defined as role profiles in `services/soc_agents.py` via `AGENT_CONFIGS` and rendered prompts (`render_base_prompt`) with per-agent tool recommendations, token limits, and thinking budgets (`services/soc_agents.py:176-509`, `services/soc_agents.py:512-561`). The built-in set includes triage, investigator, threat hunter, correlator, responder, reporter, MITRE analyst, forensics, threat intel, compliance, malware analyst, network analyst, and auto-responder. Intelligence is mostly prompt-centric: each role has explicit methodology steps and principles, then gets routed tools and model selection from `ai_model_configs` categories (`services/soc_agents.py:156-173`, `backend/api/claude.py:26-67`).

A second architecture layer is autonomous orchestration: `Orchestrator` creates investigations and `AgentRunner` executes iterative LLM+tool loops with guardrails (cost/runtime/iteration/approval gates), then a review loop approves or requests rework (`daemon/orchestrator.py:158-177`, `daemon/agent_runner.py:335-364`, `daemon/orchestrator.py:590-706`). So this is a platform with both role-based interactive agents and daemonized autonomous sub-agents.

## 3. Orchestration Pattern

Closest pattern: **hierarchical manager-worker with event-driven loops** (custom).  
- Manager: `Orchestrator` runs intake/supervision/review loops and schedules investigations (`daemon/orchestrator.py:158-162`, `daemon/orchestrator.py:207-231`, `daemon/orchestrator.py:456-571`, `daemon/orchestrator.py:590-613`).  
- Worker: `AgentRunner` executes one investigation agent per task in iterative tool-using turns (`daemon/agent_runner.py:307-464`).

Control flow example 1 (manager starts worker):
`daemon/orchestrator.py:424-426`
```python
if can_start_now:
    await self.agent_runner.start_agent(inv_record, shutdown_event)
```

Control flow example 2 (worker turn loop with tool-mediated LLM):
`daemon/agent_runner.py:397-399`, `daemon/agent_runner.py:709-710`
```python
result = await self._call_claude(inv_id, prompt)
...
result = await self._execute_tool(inv_id, tool_name, tool_input)
```

This is not a graph-state machine library; instead it is explicit loop/state orchestration around `state.json`, `plan.md`, and DB status fields (`daemon/plan_generator.py:130-199`, `daemon/plan_generator.py:310-333`).

## 4. Tools & External Integrations

- **MCP tool ecosystem (primary integration layer):** Server configs in `mcp-config.json` include GitHub, mempalace, SIEM/EDR/threat-intel tools (Splunk, SentinelOne, CrowdStrike, VirusTotal, Shodan, etc.) and custom SOC tools (`mcp-config.json:6-334`).
- **MCP server lifecycle/config loading:** `MCPService` reads `mcp-config.json`, substitutes env vars, tracks enabled servers, and builds runtime server objects (`services/mcp_service.py:326-397`, `services/mcp_service.py:259-267`).
- **Dynamic tool discovery/registration:** `MCPRegistry` aggregates active server tools and prefixes names for Claude consumption (`services/mcp_registry.py:64-93`, `services/mcp_registry.py:123-177`).
- **LLM-callable tool routing:** `AgentRunner` merges workdir tools + backend tools + MCP schemas, then dispatches each tool call to local/back-end/MCP routes with safety tiers (`daemon/agent_runner.py:601-619`, `daemon/agent_runner.py:730-756`, `daemon/agent_runner.py:840-949`).
- **Human-approval action tools:** destructive response tools are gated (`requires_approval`) and paused until approved (`daemon/agent_runner.py:99-106`, `daemon/agent_runner.py:951-999`, `daemon/agent_runner.py:1000-1073`).
- **Persistent memory layer:** MemPalace appears in both prompts and daemon persistence/search (`services/soc_agents.py:40-80`, `daemon/orchestrator.py:834-861`, `daemon/orchestrator.py:890-925`).
- **Database/case system integration:** investigations, decisions, and notifications are persisted via SQLAlchemy models/services from orchestrator and API modules (`daemon/orchestrator.py:1155-1185`, `daemon/orchestrator.py:927-975`, `backend/api/orchestrator.py:53-107`).
- **External comms:** optional Slack notification forwarding for orchestrator events (`daemon/orchestrator.py:1105-1148`).

## 5. Notable Code Walkthrough

- `services/soc_agents.py:176-561` - Defines the SOC agent library (roles, prompts, tool recommendations, token/thinking configs) and turns those into runtime `AgentProfile`s; this is the role-level “intelligence contract.”
- `backend/api/claude.py:134-325` - Main chat endpoint resolves model per agent/component, applies role prompt/tool constraints, and routes to gateway or Agent SDK path; this is the interactive control plane.
- `services/claude_service.py:3644-3910` - Implements Agent SDK streaming agent execution, MCP server injection, tool event handling, and `run_agent_task`; this is the optional agentic runtime abstraction.
- `daemon/orchestrator.py:131-177` and `daemon/orchestrator.py:245-450` - Master daemon loop creates investigations, selects workflows, writes plans/state/context, and schedules workers; this is the manager layer.
- `daemon/agent_runner.py:307-729` and `daemon/agent_runner.py:840-1073` - Worker loop executes iterative LLM/tool calls with budget and safety guardrails plus approval pauses; this is the autonomous execution engine.

## 6. Use-Case Mapping

The assigned primary use case (`Browser / Terminal Use`) looks **incorrect** for this repository. The code is centered on autonomous SOC process orchestration: queue findings, select workflow, execute multi-step investigation plans, enforce approval and budget policies, review outputs, and update cases (`daemon/orchestrator.py`, `daemon/agent_runner.py`, `daemon/plan_generator.py`). There is no browser automation stack (e.g., Playwright) or terminal-agent focus as the core product behavior. A better category is **Workflow Automation**, with a secondary flavor of RAG/memory enrichment via MemPalace.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong multi-agent role design with explicit SOC methodologies per role (`services/soc_agents.py`).
  - Real operational guardrails (cost/runtime/approval/forbidden tools) in autonomous loops (`daemon/agent_runner.py`).
  - Dynamic MCP tool ecosystem with many integrations and runtime discovery (`mcp-config.json`, `services/mcp_registry.py`).
  - Separation of manager-worker responsibilities and lifecycle observability (`daemon/orchestrator.py`, telemetry spans in runner/orchestrator).
  - Practical human-in-the-loop controls for high-impact actions (`daemon/agent_runner.py:951-1073`).

- **Limitations:**
  - Heavy reliance on prompt-engineered behavior vs. formal planner/verification models; brittle if prompts drift (`services/soc_agents.py`).
  - Control flow is complex and mostly custom loops/state files, which may be harder to formally reason about than typed graph frameworks.
  - Tool namespace overlap and dual routing paths (backend + MCP + Agent SDK) increase integration complexity (`services/claude_service.py`, `daemon/agent_runner.py`).
  - Some methods are very large (`services/claude_service.py`), making maintenance and testing harder.
  - Agent SDK path appears optional/fallback; behavior may diverge between SDK and non-SDK execution modes.

- **Research relevance:**
  - Good evidence of a production-oriented **hierarchical MAS** with manager-worker orchestration and policy guardrails.
  - Useful case study for **tool-augmented agents in high-stakes domains** (SOC/incident response) with approval gating.
  - Illustrates how **runtime tool availability (MCP registry)** can shape agent capabilities dynamically.
  - Demonstrates mixed-mode operation: interactive role agents plus autonomous background agents in one platform.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
