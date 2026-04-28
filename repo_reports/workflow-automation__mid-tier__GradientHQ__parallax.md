---
repo_name: GradientHQ/parallax
url: "https://github.com/GradientHQ/parallax"
stars: 1257
forks: 132
contributors_count: 28
last_commit_date: "2026-04-12T03:51:36+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T14:29:45.935396+00:00"
model: auto
duration_s: 83.8
clone_size_kb: 32553
uses_mas: no
final_use_case: None
---
## 1. Overview

`parallax` is a distributed LLM **inference serving** framework, not an LLM-agent application. Users run `parallax run` to start a scheduler/API server and `parallax join` on worker machines to join a P2P cluster, after which the system exposes OpenAI-compatible `/v1/chat/completions` endpoints (`src/parallax/cli.py:175-295`, `src/backend/main.py:183-249`). The core problem it solves is splitting model layers across heterogeneous nodes and routing requests through valid low-latency pipelines. In practice, users get a decentralized model-serving cluster with dynamic node join/leave handling, pipeline allocation, and request forwarding.

## 2. Agent Framework & Architecture

This repo does **not** use agent frameworks like LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex (no imports found in `*.py`; also dependencies in `pyproject.toml:19-38` show serving/network stacks, not agent orchestration libraries).

Architecture is custom distributed serving: a central scheduler process (`SchedulerManage` + `Scheduler`) coordinates node membership and layer allocation, while worker nodes run executors plus a P2P server (`src/backend/server/scheduler_manage.py:19-80`, `src/scheduling/scheduler.py:29-95`, `src/parallax/launch.py:117-188`). Request “intelligence” is algorithmic (DP/round-robin routing and allocation heuristics), not prompt/planner-driven LLM reasoning (`src/scheduling/request_routing.py:286-384`, `src/scheduling/scheduler.py:368-395`).

Although multiple runtime components cooperate, they are infrastructure services (scheduler, routers, executors, P2P handlers), not multiple coordinated LLM personas/agents.

## 3. Orchestration Pattern

Closest pattern: **hierarchical manager-worker + event-driven control loop** (for serving nodes, not LLM agents).

- Manager-worker: scheduler enqueues join/update/leave events and assigns routing paths; workers heartbeat and receive allocations (`src/backend/server/rpc_connection_handler.py:33-56`, `src/backend/server/rpc_connection_handler.py:71-110`, `src/backend/server/scheduler_manage.py:287-313`).
- Event-driven loops: scheduler runs background event and dispatch threads (`src/scheduling/scheduler.py:416-443`, `src/scheduling/scheduler.py:486-509`).

Example control flow excerpt:
- Request comes in -> scheduler resolves path -> first node stub forwards:
  - `request = RequestSignal(...)`, `self.scheduler.receive_request(request)` (`src/backend/server/scheduler_manage.py:296-298`)
  - `path, latency = self.request_router.find_optimal_path(...)` (`src/scheduling/scheduler.py:386-394`)

## 4. Tools & External Integrations

- **P2P overlay / RPC (`lattica`)**: cluster membership, peer discovery, RPC method exposure (`src/backend/server/scheduler_manage.py:204-285`, `src/parallax/p2p/server.py:436-460`).
- **FastAPI + Uvicorn HTTP serving**: OpenAI-compatible chat and cluster APIs (`src/backend/main.py:25-33`, `src/backend/main.py:183-189`, `src/parallax/server/node_chat_http_server.py:42-54`).
- **Executor backends (`sglang`, `vllm`, `mlx`)**: backend selection and executor spawning (`src/parallax/server/executor/factory.py:90-107`).
- **Hugging Face model fetch**: metadata/model download and config loading (`src/parallax/utils/utils.py:287-295`).
- **ZeroMQ IPC**: communication between P2P server and local executor processes (`src/parallax/utils/utils.py:68-108`, `src/parallax/p2p/server.py:133-139`).
- **HTTP client forwarding (`httpx`, `aiohttp`)**: inter-component forwarding and streaming (`src/backend/server/rpc_connection_handler.py:123-137`, `src/backend/server/request_handler.py:44-55`).
- **Graph pathfinding (`dijkstar`)**: non-scheduler-mode route construction (`src/parallax/p2p/server.py:580-603`).

No MCP/browser automation/RAG/vector DB toolchain is wired here.

## 5. Notable Code Walkthrough

- `src/parallax/cli.py:175-295` - Main operator entrypoint (`run`, `join`, `chat`) that launches scheduler or worker modes with relay/network settings; defines how users actually operate the system.
- `src/backend/main.py:183-249` - Central API server exposing `/v1/chat/completions` and cluster management endpoints, wiring HTTP requests to scheduler-aware forwarding.
- `src/backend/server/scheduler_manage.py:170-203` - Creates and runs the scheduler thread plus P2P RPC layer; this is the bridge between control plane and networking.
- `src/scheduling/scheduler.py:416-509` - Core orchestration loops (event handling + request dispatch) and bootstrap gating; captures cluster lifecycle logic.
- `src/scheduling/request_routing.py:286-384` - Dynamic-programming routing over allocated layer shards to compute minimum-latency node paths per request.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** does not match the codebase well. This repository automates **inference serving operations** (node bootstrap, layer allocation, request routing, failover/rebalance), not multi-step business/tool workflows executed by LLM agents. It is better categorized as **None** under your allowed taxonomy, because it is primarily distributed model-serving infrastructure rather than agentic workflow/codegen/RAG/browser simulation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong systems design for decentralized serving across heterogeneous nodes (`src/parallax/launch.py:128-188`, `src/parallax/p2p/server.py:496-556`).
  - Clear separation of control plane (scheduler) and data plane (executor/P2P forwarding).
  - Multiple routing strategies (DP and fixed-pipeline RR) with explicit capacity/latency modeling (`src/scheduling/request_routing.py:286-384`, `src/scheduling/request_routing.py:561-853`).
  - Robust join/leave/heartbeat event handling and rebalancing logic (`src/scheduling/scheduler.py:540-637`).

- **Limitations:**
  - No true multi-agent LLM runtime (no planner-worker LLM roles, no prompt-based agent coordination).
  - Routing/allocation decisions are heuristic/algorithmic and may be brittle under highly dynamic network conditions.
  - Several long blocking loops/retries in networking paths can complicate fault handling and observability (`src/parallax/p2p/server.py:475-492`, `src/backend/server/request_handler.py:57-97`).
  - Heavy backend complexity (SGLang/vLLM/MLX branches) increases operational surface area.

- **Research relevance:**
  - Useful evidence for **distributed LLM serving orchestration**, not agentic cognition.
  - Demonstrates practical layer-sharding + route optimization in decentralized environments.
  - Illustrates event-driven membership management and adaptive pipeline reconfiguration under churn.
  - Relevant to systems papers on P2P inference and scheduling, less so to multi-agent LLM interaction studies.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
