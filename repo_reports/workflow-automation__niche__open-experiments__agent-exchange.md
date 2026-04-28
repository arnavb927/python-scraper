---
repo_name: open-experiments/agent-exchange
url: "https://github.com/open-experiments/agent-exchange"
stars: 384
forks: 284
contributors_count: 3
last_commit_date: "2026-04-08T23:08:53+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 2
architecture_labels: [LangChain, CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T17:23:03.101654+00:00"
model: auto
duration_s: 85.9
clone_size_kb: 219969
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`open-experiments/agent-exchange` is a marketplace-style platform where one agent can outsource work to other agents through bidding, contract award, and settlement services, with a runnable Docker demo that includes both exchange services and demo agents. In practice, users run `demo/aex/docker-compose.yml`, then submit a request (via UI or A2A endpoint) to an orchestrator agent, which decomposes the task and routes subtasks to provider agents. The Go backend services handle market mechanics (provider discovery, bid intake, evaluation, contract lifecycle, and settlement), while Python demo agents handle LLM reasoning and A2A task execution. So the repo solves “agent-to-agent workflow exchange” rather than just “single chatbot inference.”

## 2. Agent Framework & Architecture

The LLM-agent layer is **LangGraph + LangChain** (not CrewAI/AutoGen in runtime code). This is explicit in imports like `langgraph.graph.StateGraph` and `langchain_anthropic.ChatAnthropic` in `demo/aex/agents/common/base_agent.py:9-13` and `demo/aex/agents/orchestrator/agent.py:11-14`. The demo dependencies also pin `langgraph`, `langchain`, and `langchain-anthropic` in `demo/aex/agents/common/requirements.txt:4-10`.

Architecture is split into two layers:

1. **Exchange infrastructure (Go microservices)**: `aex-work-publisher`, `aex-bid-gateway`, `aex-bid-evaluator`, `aex-contract-engine`, `aex-provider-registry`, etc. These are protocol/business services, not LLM agents (`src/aex-*/internal/service/*.go`).
2. **Runtime LLM agents (Python demo)**: orchestrator + specialist agents. `OrchestratorAgent` decomposes requests, discovers providers, and calls provider agents via A2A JSON-RPC (`demo/aex/agents/orchestrator/agent.py:104-128`, `376-445`). Specialist agents (e.g., legal-agent-a/b/c) run prompt-driven inference with Claude and return results (`demo/aex/agents/legal-agent-a/agent.py:21-30`, `101-113`).

“Intelligence” lives mostly in prompt templates + LLM decomposition logic in the orchestrator (`ORCHESTRATOR_PROMPT`) and role-specific prompts in provider agents.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)** with marketplace-assisted routing.

The orchestrator is the manager: it decomposes the user task, discovers/selects providers, then invokes workers sequentially via A2A (`demo/aex/agents/orchestrator/agent.py:113-128`, `284-333`, `376-398`).

Example control flow:

```demo/aex/agents/orchestrator/agent.py:113-126
# Step 1: Decompose task
subtasks = await self._decompose_task(user_content)
...
# Step 2: Discover providers via AEX for each subtask
await self._discover_providers(subtasks)

# Step 3: Execute subtasks via A2A
results = await self._execute_subtasks(subtasks)
```

Worker invocation happens through A2A JSON-RPC:

```demo/aex/agents/orchestrator/agent.py:405-415
payload = {
    "jsonrpc": "2.0",
    "method": "message/send",
    "id": subtask.id,
    "params": {
        "message": {"role": "user", "parts": [{"type": "text", "text": subtask.input}]}
    },
}
```

The Go exchange services themselves are a **service pipeline** (publish → bid → evaluate → award), but not multi-agent LLM orchestration.

## 4. Tools & External Integrations

- **Anthropic Claude (LLM inference)**: via `ChatAnthropic` in orchestrator and legal agents (`demo/aex/agents/orchestrator/agent.py:11,84-98`; `demo/aex/agents/legal-agent-a/agent.py:8,48-62`).
- **LangGraph execution graph**: base agent and per-agent graph skeleton (`demo/aex/agents/common/base_agent.py:9,54-56`; `demo/aex/agents/legal-agent-a/agent.py:64-67`).
- **A2A protocol over HTTP JSON-RPC**: server and message/task lifecycle in `demo/aex/agents/common/a2a_server.py:101-122`, `131-179`, `180-227`.
- **AEX Gateway HTTP APIs**: provider registration, subscription, bid submit, provider search, work submit (`demo/aex/agents/common/aex_client.py:76-122`, `123-153`, `154-180`, `217-239`, `240-270`).
- **MongoDB persistence**: configured and used across services (`demo/aex/docker-compose.yml:8-18`; `src/aex-provider-registry/internal/store/mongo.go:20-27` and many CRUD/index methods).
- **NATS JetStream event bus (optional / partially wired)**: publisher supports NATS + webhook fallback (`src/internal/events/publisher.go:19-31`, `77-84`, `99-119`); NATS client in `src/internal/nats/client.go:57-67`, `139-167`.
- **HTTP webhooks**: event publisher can POST signed webhooks with retries (`src/internal/events/publisher.go:130-139`, `144-166`, `189-205`).
- **No browser automation / vector DB / RAG pipeline** observed in core runtime paths.

## 5. Notable Code Walkthrough

- `demo/aex/agents/orchestrator/agent.py:24-60,148-185,284-445` - Defines the manager agent: LLM prompt-based task decomposition, provider discovery (AEX + fallback mapping), and A2A execution of subtasks.
- `demo/aex/agents/common/base_agent.py:30-61,63-124,125-206` - Shared agent runtime abstraction: A2A message handling, bid request handling, and delegation to agent-specific processing logic.
- `demo/aex/agents/common/a2a_server.py:101-122,131-179,180-227` - Implements A2A JSON-RPC server endpoints (`message/send`, `tasks/get`, etc.), turning agent handlers into network-accessible worker services.
- `src/aex-work-publisher/internal/service/service.go:46-123,207-247` - Starts exchange workflow by validating work, persisting it, notifying providers, and transitioning state for bid windows.
- `src/aex-bid-evaluator/internal/service/evaluator.go:88-174,185-193` - Scores bids using weighted criteria (price, trust, confidence, SLA, certification) and ranks providers, which is the market decision core.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. The demo implements automated multi-step workflows where one orchestrator agent decomposes a user goal into subtasks, discovers/selects specialized providers, executes them, and aggregates outputs (`demo/aex/agents/orchestrator/agent.py:113-128`, `446-474`). The exchange services automate the commercial workflow around that execution (work publication, bidding, evaluation, award, completion) in a deterministic pipeline (`src/aex-work-publisher/internal/service/service.go:46-123`; `src/aex-contract-engine/internal/service/service.go:33-126,203-260`). This is broader than pure chatbot behavior and not primarily RAG or codegen.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear separation between market infrastructure and LLM-agent execution layers.
  - Concrete multi-agent manager/worker runtime using A2A calls, not just conceptual docs.
  - Realistic economic coordination (bid scoring, trust/certification factors) in evaluator logic.
  - Good interoperability stance: provider discovery + agent cards + A2A endpoints.
  - End-to-end demo deployable via Docker with multiple competing providers.

- **Limitations:**
  - LangGraph usage is thin; `StateGraph` is imported but not deeply used as a real branching state machine in agents.
  - Core Go services are mostly non-LLM; MAS behavior is concentrated in demos, not the exchange backend.
  - Event bus is partly aspirational: publisher supports NATS, but flow still relies heavily on HTTP paths and fallback behavior.
  - Some orchestrator provider routing is hardcoded demo fallback (`demo_agents` map), reducing dynamic autonomy.
  - Security/auth in demo agent layer is permissive (e.g., default token validation accepts all in A2A handler).

- **Research relevance:**
  - Useful as evidence of **market-based coordination for agent ecosystems** (bidding + trust + contract lifecycle).
  - Demonstrates a **hybrid MAS architecture**: LLM orchestration on top of deterministic service infrastructure.
  - Shows practical **manager-worker decomposition with networked specialist agents** via A2A JSON-RPC.
  - Provides a case study of **agent interoperability protocols** (A2A, agent cards, registry search) in an enterprise workflow setting.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
