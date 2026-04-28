---
repo_name: isekOS/ISEK
url: "https://github.com/isekOS/ISEK"
stars: 560
forks: 42
contributors_count: 7
last_commit_date: "2025-12-09T03:12:17+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T16:15:13.499323+00:00"
model: auto
duration_s: 73.0
clone_size_kb: 48461
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`isekOS/ISEK` is a Python + Node framework for exposing LLM agents as networked services that can call each other using the A2A (agent-to-agent) protocol, either over HTTP or via a libp2p relay. A developer typically runs an agent server (wrapping a `pydantic_ai.Agent`) and then runs a client script that sends tasks to that agent endpoint or peer ID. The framework handles agent-card discovery, JSON-RPC message formatting, task-state updates, and optional on-chain identity registration for agents. In practice, what you get is infrastructure for distributed agent interoperability, not a prebuilt end-user app workflow.

## 2. Agent Framework & Architecture

The repo is **not CrewAI/LangGraph/AutoGen** in code. It uses:
- `pydantic-ai` for LLM agent execution (`pydantic_ai.Agent`) in `isek/adapter/pydantic_ai_adapter.py:1-177`
- `a2a-sdk` server/client primitives (`A2AClient`, `DefaultRequestHandler`, `AgentExecutor`) in `isek/node/node_v3_a2a.py:8-15` and `isek/adapter/pydantic_ai_adapter.py:3-15`
- Custom transport/orchestration glue around A2A + libp2p in `isek/protocol/a2a_protocol_v2.py:17-190` and `isek/protocol/p2p/p2p_server.js:1-282`

Architecture-wise, each agent is a node exposing an A2A HTTP server (`Node.create_server` + `Node.build_server`) with a declared `AgentCard` and an executor that streams task updates. Intelligence is mainly inside the wrapped LLM agent prompt/model call (`self._agent.run(query)`), while the framework focuses on communication and lifecycle plumbing (`TaskUpdater`, state transitions). The multi-agent aspect is decentralized: any node/client can discover another node’s card and send JSON-RPC A2A messages directly.

A second layer optionally bridges A2A over p2p: Python starts a local Node.js bridge process; that bridge dials peers through a relay and forwards incoming A2A payloads to local agent HTTP endpoints (`p2p_server.js` handler forwards to `http://localhost:<agent_port>/`).

## 3. Orchestration Pattern

Closest match: **swarm (peer-to-peer) with request/response task execution**.

Why:
- There is no central planner/manager graph; nodes send tasks directly to other agents via A2A (`Node.send_message`) and can route over p2p peer addresses (`A2AProtocolV2.send_message`).
- Control flow is message-driven between peers; each receiving agent independently executes and emits task status updates.

Example control flow (client -> remote agent):
`isek/node/node_v3_a2a.py:83-108`
```python
agent_card_data = await self.get_agent_card_by_url(agent_url)
agent_card = AgentCard(**agent_card_data)
msg_params = MessageSendParams(
    message=Message(role=Role.user, parts=[Part(TextPart(text=query))], messageId=uuid4().hex)
)
client = A2AClient(httpx_client, agent_card=agent_card)
response = await client.send_message(
    SendMessageRequest(id=uuid4().hex, params=msg_params)
)
```

Example control flow (agent executor state machine for one task):
`isek/adapter/pydantic_ai_adapter.py:141-167`
```python
async for item in self.agent.stream(query, task.context_id):
    is_task_complete = item["is_task_complete"]
    require_user_input = item["require_user_input"]
    message = new_agent_text_message(content, task.context_id, task.id)
    if is_task_complete:
        await updater.complete(message)
    elif require_user_input:
        await updater.update_status(TaskState.input_required, message)
    else:
        await updater.update_status(TaskState.working, message)
```

## 4. Tools & External Integrations

- **LLM runtime (`pydantic-ai`)**: underlying model call via `Agent.run()` in `isek/adapter/pydantic_ai_adapter.py:55-56,91-92`; example model configured as `gpt-4` in `examples/Agent_servers/Pydantic/openai_agent_a2a.py:37-40`.
- **A2A protocol SDK (`a2a-sdk`)**: server app/request handler/task store in `isek/node/node_v3_a2a.py:8-14,189-195`; executor/task/event APIs in `isek/adapter/pydantic_ai_adapter.py:3-7,115-177`.
- **HTTP transport (`httpx`)**: fetch agent cards and send A2A requests in `isek/node/node_v3_a2a.py:48-72,103-108`; p2p bridge local API calls in `isek/protocol/a2a_protocol_v2.py:125-166`.
- **libp2p + Express bridge (Node.js)**: peer networking and relay dialing in `isek/protocol/p2p/p2p_server.js:90-129,192-206`; relay server in `isek/protocol/p2p/relay.js:26-61`.
- **Blockchain identity (Web3 / ERC-8004-style registry)**: wallet creation and optional identity registration in `isek/web3/wallet_manager.py:51-103` and `isek/web3/isek_identiey.py:144-201`.
- **No MCP / vector DB / browser automation / RAG pipeline** found in repository source.

## 5. Notable Code Walkthrough

- `isek/node/node_v3_a2a.py:28-222` - Core node abstraction: serves A2A endpoints, retrieves remote `AgentCard`s, sends `message/send` requests, and bootstraps uvicorn + request handlers. This is the main interoperability backbone.
- `isek/adapter/pydantic_ai_adapter.py:22-177` - Adapter and executor glue from `pydantic_ai.Agent` into A2A `AgentExecutor`, including streaming, task creation, and task-state transitions (`working`, `input_required`, `complete`).
- `isek/protocol/a2a_protocol_v2.py:17-190` - Python-side protocol helper that starts the local p2p bridge process and wraps peer messaging as JSON-RPC over local HTTP (`/call_peer`).
- `isek/protocol/p2p/p2p_server.js:50-282` - Node bridge that runs libp2p transport, connects to relay, handles stream protocol requests, and forwards payloads to local agent HTTP service.
- `examples/Agent_servers/Pydantic/openai_agent_a2a_p2p.py:11-75` - End-to-end reference composition showing how a real agent is declared (`AgentCard`), wrapped, optionally exposed via p2p, and served.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** is reasonable, though this repo is more accurately “agent network middleware for workflow composition.” It automates a workflow where an incoming task is routed to an agent endpoint, executed by an LLM wrapper, tracked through task states, and returned via standardized A2A responses (`isek/node/node_v3_a2a.py`, `isek/adapter/pydantic_ai_adapter.py`). It also automates cross-node communication and transport concerns (HTTP vs p2p relay) so multi-agent workflows can be distributed across machines (`isek/protocol/a2a_protocol_v2.py`, `isek/protocol/p2p/p2p_server.js`).  

So the best final category remains **Workflow Automation** (infrastructure-level, not domain-specific business workflows).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clean separation between agent reasoning (`pydantic-ai`) and transport/orchestration (`a2a-sdk` + Node wrapper).
  - Practical decentralized transport option via libp2p relay bridge, not just localhost HTTP.
  - Standardized metadata and discoverability through `AgentCard` and well-known endpoint usage.
  - Task lifecycle/status signaling is explicit (`working`/`input_required`/`complete`) and easy to observe.
  - Optional on-chain identity registration provides a concrete trust/identity extension for multi-agent networks.

- **Limitations:**
  - No built-in planner/router that composes multiple specialized agents into a single autonomous pipeline.
  - Examples are mostly single-agent servers plus client calls; multi-agent collaboration logic is left to users.
  - Security/authn/authz for inter-agent calls appears minimal (open HTTP endpoints + relay-address assumptions).
  - Limited resilience patterns (retry policy, queue durability, backpressure, and robust failure recovery are sparse).
  - Some code duplication/inconsistency (e.g., `open_ai_sdk_adapter.py` mirrors pydantic adapter patterns) suggests evolving architecture.

- **Research relevance:**
  - Useful evidence of a lightweight, protocol-centric MAS stack where interoperability is prioritized over centralized planning.
  - Demonstrates how A2A task semantics can be layered over heterogeneous transports (HTTP and p2p relay).
  - Shows an early pattern for combining decentralized networking with optional blockchain identity in agent ecosystems.
  - Serves as a case study of “infrastructure-first” MAS design versus “planner-first” MAS design.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
