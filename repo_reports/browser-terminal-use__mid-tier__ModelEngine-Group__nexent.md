---
repo_name: ModelEngine-Group/nexent
url: "https://github.com/ModelEngine-Group/nexent"
stars: 4328
forks: 576
contributors_count: 210
last_commit_date: "2026-04-18T03:08:42+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T12:19:33.568551+00:00"
model: auto
duration_s: 97.3
clone_size_kb: 70849
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`nexent` is a full-stack agent platform (backend + SDK) for building and running configurable AI agents with tools, memory, and sub-agent delegation, exposed mainly through `/agent/run` streaming APIs. A user configures an agent (prompts, tools, model, sub-agents) in the backend database/UI, then runs it via API; the runtime materializes that config into executable agent objects. At execution time, it can do ReAct-style tool use, call internal sub-agents, invoke external A2A agents, and stream intermediate/final outputs to clients. The practical output is not a single CLI assistant; it is a hosted orchestration system for reusable production agents with governance features (versioning, permissions, import/export, MCP tool federation).  

## 2. Agent Framework & Architecture

The runtime is built on **`smolagents`**, not LangGraph/CrewAI/AutoGen. This is directly visible in imports and inheritance: `CoreAgent` subclasses `smolagents.agents.CodeAgent` (`sdk/nexent/core/agents/core_agent.py:12-16`, `210-213`), and MCP integration uses `smolagents.ToolCollection` (`sdk/nexent/core/agents/run_agent.py:6`, `105-111`).

Architecture is a configurable **manager + sub-agent tree**. The backend compiles DB config into `AgentConfig` recursively (`backend/agents/create_agent_info.py:272-306`) and includes both local managed agents and optional external A2A agents (`303-305`, `384-415`). `NexentAgent.create_single_agent()` recursively instantiates sub-agents and appends external A2A wrappers into `managed_agents` (`sdk/nexent/core/agents/nexent_agent.py:226-247`, `250-263`).

“Intelligence” lives in three places:  
- prompt templates (`backend/prompts/manager_system_prompt_template_en.yaml`, `managed_system_prompt_template_en.yaml`) that explicitly instruct Think/Code/Observe and delegation behavior;  
- `CoreAgent._step_stream()` (LLM call -> parse executable code -> execute tools/agents) (`sdk/nexent/core/agents/core_agent.py:270-383`);  
- backend assembly logic that injects memory, available tools, skill metadata, and sub-agent lists into system prompts (`backend/agents/create_agent_info.py:324-393`).  

## 3. Orchestration Pattern

Closest pattern: **hierarchical (manager-worker), with recursive composition**.

Control flow is manager-to-worker function-style delegation, where parent agent code can call sub-agent objects as Python-callable tools. Example wiring:

```python
sdk/nexent/core/agents/nexent_agent.py:226-231
managed_agents_list = [
    self.create_single_agent(sub_agent_config) 
    for sub_agent_config in agent_config.managed_agents
]
```

```python
sdk/nexent/core/agents/core_agent.py:433-435
self.python_executor.send_tools(
    {**self.tools, **self.managed_agents})
```

This is not a graph state machine (no LangGraph node/edge scheduler), nor swarm peer-to-peer. It is a central agent loop (`_run_stream`) with optional hierarchical delegation and optional remote A2A worker calls (`sdk/nexent/core/agents/a2a_agent_proxy.py:704-775`).

## 4. Tools & External Integrations

- **MCP tool servers (local + remote)**: runtime filters used MCP servers, builds transport/auth config, and loads tool collection at run time (`backend/agents/create_agent_info.py:627-663`, `sdk/nexent/core/agents/run_agent.py:102-106`).  
- **A2A external agent protocol** (JSON-RPC / HTTP+JSON, streaming): proxy/client and wrapper for treating remote agents as managed sub-agents (`sdk/nexent/core/agents/a2a_agent_proxy.py:73-77`, `183-236`, `345-385`, `704-775`).  
- **Terminal execution via SSH**: `TerminalTool` executes shell commands on remote SSH sessions with session reuse (`sdk/nexent/core/tools/terminal_tool.py:17-23`, `113-134`, `335-372`).  
- **Web search APIs**: Tavily, Exa, Linkup tools are first-class (`sdk/nexent/core/tools/tavily_search_tool.py:17-21`, `72-79`; `sdk/nexent/core/tools/__init__.py:1-10`).  
- **RAG / retrieval integrations**: knowledge-base search tool + vector backends + rerank model wiring (`backend/agents/create_agent_info.py:449-463`, `352-373`; `sdk/nexent/core/tools/knowledge_base_search_tool.py`).  
- **Filesystem tools**: create/read/delete file & directory, move/list directory (`sdk/nexent/core/tools/__init__.py:10-19`).  
- **Email tools**: send/get email (`sdk/nexent/core/tools/__init__.py:2`, `7`).  
- **Multimodal tools**: image/text analysis tool wiring with VLM/LLM and storage client (`backend/agents/create_agent_info.py:475-485`).  
- **Memory service**: multi-level memory retrieval before run and async writeback after final answer (`backend/agents/create_agent_info.py:337-347`; `backend/services/agent_service.py:666-675`).  

## 5. Notable Code Walkthrough

- `sdk/nexent/core/agents/core_agent.py:270-383,512-565` - Core ReAct-like execution engine: model inference, code extraction, tool/agent execution in Python interpreter, and step streaming/finalization. This is the key runtime “agent brain.”
- `sdk/nexent/core/agents/nexent_agent.py:190-268` - Agent factory that materializes one configured agent, recursively builds managed sub-agents, and attaches external A2A wrappers. This defines actual multi-agent composition.
- `backend/agents/create_agent_info.py:272-416,591-673` - Converts persisted platform config into executable `AgentConfig` + `AgentRunInfo`, including prompt rendering, tool metadata, memory retrieval, and MCP host filtering.
- `sdk/nexent/core/agents/a2a_agent_proxy.py:183-236,345-385,704-775` - External agent interoperability layer (A2A). Important because it extends coordination beyond local agent tree into distributed multi-agent calls.
- `backend/services/agent_service.py:1798-1967,1661-1750` - Streaming runtime orchestration (`run_agent_stream`) with memory-aware fallback paths and SSE chunking, i.e., how the platform serves agent execution in production.

## 6. Use-Case Mapping

Assigned label `Browser / Terminal Use` is **partially true but not primary**. The code clearly supports terminal actions (`TerminalTool`) and can access browser-like capabilities indirectly through MCP/outer APIs, but the repository’s core is a **general agent orchestration platform** with memory, versioning, tool governance, and sub-agent routing.

A better primary category is **Workflow Automation**: agents orchestrate multi-step tasks using tools/sub-agents, with backend-managed configuration and execution pipelines (`backend/services/agent_service.py`, `backend/agents/create_agent_info.py`, `sdk/nexent/core/agents/nexent_agent.py`). It also has a strong secondary flavor of RAG+Agents due to built-in retrieval and memory layers.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Real multi-agent runtime via recursive manager/sub-agent composition, not just prompt-role simulation.
  - Practical interoperability: local tools + MCP + external A2A agents in one execution model.
  - Production-oriented architecture (streaming SSE, versioning, permissions, import/export, availability checks).
  - Rich tool surface (terminal, filesystem, search, RAG, email, multimodal) enabling complex workflows.
  - Prompt templating injects dynamic context (memory/skills/tools), making behavior configurable per tenant/agent.

- **Limitations:**
  - Orchestration is mostly imperative/hierarchical; lacks explicit graph-level planning, scheduling, or recovery semantics.
  - Very large service modules (e.g., `agent_service.py`) increase coupling and maintenance complexity.
  - Some language-specific hardcoding remains in prompts/strings (mixed zh/en content), which may complicate consistent behavior.
  - Tool safety/policy enforcement appears prompt-driven more than strongly sandboxed at runtime.
  - External A2A and MCP reliability/error paths exist but can still degrade into generic failures.

- **Research relevance:**
  - Evidence of **platformized multi-agent systems** where agent topology is data-driven (DB config -> runtime tree).
  - Useful example of **hybrid coordination**: local tool-using agents + remote agent protocols (A2A/MCP).
  - Illustrates **hierarchical agent orchestration** in production APIs with streaming interaction loops.
  - Demonstrates integration of memory/retrieval with delegated sub-agent workflows in a configurable control plane.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
