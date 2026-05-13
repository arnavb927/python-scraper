---
repo_name: a2aproject/A2A
url: "https://github.com/a2aproject/A2A"
stars: 23373
forks: 2364
contributors_count: 140
last_commit_date: "2026-04-21T16:53:57+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 9
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-05-05T06:25:46.272117+00:00"
model: auto
duration_s: 199.7
clone_size_kb: 3523
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`a2aproject/A2A` is primarily a **protocol-specification repository** for agent interoperability, not a runnable multi-agent application by itself. What users practically “run” here is the specification/tooling workflow (e.g., proto/schema generation and docs), then they implement servers/clients in separate SDK repos or samples. The core artifact is the A2A protocol contract (`specification/a2a.proto`), which defines how one agent-facing service exposes discovery, task lifecycle, streaming, and messaging APIs. In practice, developers use this repo to standardize communication between independently built agents, then use `a2a-python`, `a2a-js`, etc., to build concrete systems.

## 2. Agent Framework & Architecture

From the code in this repository, there is **no direct runtime dependency on LangGraph, CrewAI, AutoGen, LangChain, or LlamaIndex**. The main implementation artifact is protocol definition (`specification/a2a.proto`), plus documentation/tutorial references to SDK classes in other repos (e.g., `AgentExecutor`, `DefaultRequestHandler`) (`docs/tutorials/python/4-agent-executor.md:3-12`, `docs/tutorials/python/5-start-server.md:19-31`).

Architecture-wise, this repo defines a **client/server agent protocol boundary**: `A2AService` methods for sending messages, creating/streaming task updates, task retrieval/cancellation, and agent-card discovery extensions (`specification/a2a.proto:19-140`). The “intelligence” (LLM prompts, planners, tool-calling internals) is intentionally opaque and out-of-scope for this repo; the protocol standardizes exchange objects (`Message`, `Task`, `Artifact`, `AgentCard`, `AgentSkill`) and lifecycle semantics (`TaskState`) (`specification/a2a.proto:163-447`).

So the architecture here is best described as a **transport/contract layer for agentic systems**, not an in-repo multi-agent runtime graph.

## 3. Orchestration Pattern

Closest match: **event-driven task protocol (other)**.

Control flow is modeled as RPC + streaming events: client submits work; server emits task/event progression (`SUBMITTED` → `WORKING` → `COMPLETED`/etc.) through stream responses.

```19:33:specification/a2a.proto
service A2AService {
  rpc SendMessage(SendMessageRequest) returns (SendMessageResponse) {
    option (google.api.http) = {
      post: "/message:send"
      body: "*"
    };
  }
  rpc SendStreamingMessage(SendMessageRequest) returns (stream StreamResponse) {
    option (google.api.http) = {
      post: "/message:stream"
      body: "*"
    };
  }
```

```774:786:specification/a2a.proto
message StreamResponse {
  oneof payload {
    Task task = 1;
    Message message = 2;
    TaskStatusUpdateEvent status_update = 3;
    TaskArtifactUpdateEvent artifact_update = 4;
  }
}
```

The lifecycle semantics and parallel follow-ups are explicitly documented (`docs/topics/life-of-a-task.md:98-110`), reinforcing that orchestration is state/event-based rather than manager-worker code in this repo.

## 4. Tools & External Integrations

This repository itself does **not wire concrete external tools/services into an agent runtime** (no in-repo browser automation, vector DB adapters, search clients, or shell-tool executors).  
What it does provide:

- **Protocol transports and APIs**: JSON-RPC/HTTP(+S)/gRPC bindings via protobuf service definitions (`specification/a2a.proto:19-140`, `336-349`).
- **Agent discovery interface**: standardized `AgentCard` and `AgentSkill` metadata for capability advertisement (`specification/a2a.proto:352-447`).
- **Push notification integration points**: callback URL + auth metadata for async task updates (`specification/a2a.proto:463-478`, `89-139`).
- **MCP relationship (conceptual, not wired code here)**: docs explain A2A (agent-agent) vs MCP (agent-tool) complementarity (`docs/topics/a2a-and-mcp.md:10-20`, `24-35`, `56-60`).
- **SDK/sample references** (external repos): Python tutorial points to `a2a-samples` and SDK helpers for Starlette/Uvicorn deployment (`docs/tutorials/python/5-start-server.md:5-8`, `44-47`).

## 5. Notable Code Walkthrough

- `specification/a2a.proto:19-140` — Defines the core `A2AService` RPC surface (`SendMessage`, streaming, task CRUD, push config), which is the canonical interaction contract every compliant agent server/client must implement.
- `specification/a2a.proto:163-322` — Encodes the task/event model (`Task`, `TaskState`, `TaskStatusUpdateEvent`, `TaskArtifactUpdateEvent`) that drives long-running and streaming agent workflows.
- `specification/a2a.proto:352-447` — Defines `AgentCard`, capabilities, and `AgentSkill`, enabling discovery and interoperability across heterogeneous agent implementations.
- `docs/tutorials/python/4-agent-executor.md:3-12` and `44-55` — Describes the SDK executor contract (`execute`, `cancel`) and event emission sequence, showing how concrete agent logic is expected to plug into A2A.
- `docs/topics/life-of-a-task.md:35-69` and `98-110` — Clarifies message-vs-task behavior and parallel follow-up execution semantics; this is key for understanding practical orchestration behavior expected by the protocol.

## 6. Use-Case Mapping

The assigned label `RAG + Agents` is **not the best fit for this repository itself**. I did not find in-repo RAG pipeline implementation (no retriever/vector store/index/query stack wiring). Instead, the repo provides a standardized protocol for **multi-agent interoperability and long-running task coordination**, independent of whether those agents use RAG internally.

A better classification for this repo is **Workflow Automation**: it formalizes how agents discover each other, negotiate capabilities, exchange stateful tasks, and coordinate asynchronous/streaming work across systems (`specification/a2a.proto:19-140`, `163-208`; `docs/topics/life-of-a-task.md:45-69`, `98-110`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong, explicit protocol contract with typed lifecycle/state semantics in protobuf (`specification/a2a.proto`).
  - Clear support for async/streaming interactions and push notifications, not just request/response.
  - Interoperability-first design through `AgentCard`/`AgentSkill` abstractions.
  - Framework-agnostic positioning; avoids coupling to one agent stack.
  - Good conceptual documentation on task immutability, refinements, and parallel follow-ups.

- **Limitations:**
  - No executable in-repo LLM agent orchestration engine to inspect end-to-end runtime behavior.
  - No concrete built-in tool integrations (RAG stores, browser agents, code execution tools) in this repo.
  - Tutorials rely on external SDK/sample repositories, so implementation details are fragmented.
  - Security/auth flows are specified but not demonstrated via concrete in-repo server/client code.
  - Limited direct benchmarking/evaluation artifacts for multi-agent performance.

- **Research relevance:**
  - Useful evidence for **standardized inter-agent protocol design** (discovery, capability description, lifecycle).
  - Relevant to studies of **event-driven coordination semantics** for long-running AI tasks.
  - Supports analysis of **agent interoperability across heterogeneous frameworks/vendors**.
  - Illustrates protocol-layer separation between **agent-agent collaboration (A2A)** and **agent-tool interaction (MCP)**.

## 8. Machine-readable classification

MAS_RELATED: yes  
USES_MAS: yes  
FINAL_USE_CASE: Workflow Automation
