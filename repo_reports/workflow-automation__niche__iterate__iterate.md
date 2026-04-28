---
repo_name: iterate/iterate
url: "https://github.com/iterate/iterate"
stars: 150
forks: 14
contributors_count: 15
last_commit_date: "2026-04-21T23:00:02+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 1
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T18:03:08.444632+00:00"
model: auto
duration_s: 88.6
clone_size_kb: 36289
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`iterate/iterate` is a full-stack platform for running long-lived coding/workflow agents tied to projects, PRs, and chat/event streams rather than a standalone “single script” agent demo. In practice, users run the OS/daemon stack (`pnpm dev` or app-specific dev commands) and the system provisions agent sessions that receive event payloads (for example GitHub PR signals) and route them into an agent harness (`README.md:24-39`, `apps/daemon/server/routers/agents.ts:508-603`). The repo’s core runtime behavior is: create or recover an agent route, forward prompt events, execute via an agent backend (notably OpenCode or a Cloudflare Durable Object agent), and stream/update status back into the platform (`apps/daemon/server/routers/opencode.ts:35-50`, `apps/agents/src/durable-objects/iterate-agent.ts:105-182`). The output a user gets is automated workflow execution (PR follow-up, tool-calling scripts, assistant responses) embedded in Iterate’s project/machine lifecycle rather than a local REPL chatbot.

## 2. Agent Framework & Architecture

This repo uses a **custom architecture** with Cloudflare primitives, not LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex. The concrete runtime imports are Cloudflare `agents` SDK (`Agent`, `routeAgentRequest`) and `@cloudflare/codemode` (`DynamicWorkerExecutor`, tool providers), plus custom event contracts (`apps/agents/src/entry.workerd.ts:3-11`, `apps/agents/src/durable-objects/agent-processor.ts:1-9`).

At a high level there are two agent execution planes:

1. **Cloudflare Durable Object agent (`IterateAgent`)**: receives websocket stream frames, reduces state into KV, and triggers side effects (`afterAppend`) such as LLM calls or codemode script execution (`apps/agents/src/durable-objects/iterate-agent.ts:140-176`, `apps/agents/src/durable-objects/agent-processor.ts:49-109`).
2. **Daemon harness routing plane**: maps logical `agentPath` to a concrete backend route/session (`/opencode/sessions/:id`, etc.), creates sessions on demand, forwards incoming events, and tracks lifecycle/status (`apps/daemon/server/routers/agents.ts:249-482`, `apps/daemon/server/routers/opencode.ts:60-170`).

“Intelligence” lives primarily in:
- event-driven processor logic (`reduce` + `afterAppend`) rather than explicit planner/graph nodes,
- prompt construction for automation workflows (e.g., GitHub PR routing prompt builder),
- tool execution through codemode providers (OpenAPI + MCP) (`apps/os/backend/integrations/github/github-pr-agent.ts:87-157`, `apps/agents/src/lib/openapi-tool-provider.ts:67-181`).

## 3. Orchestration Pattern

Closest match: **event-driven workflow orchestration** (with per-agent sequential handling), not hierarchical multi-agent planning.

Control flow is driven by inbound events and route lookup/creation:

```105:182:apps/agents/src/durable-objects/iterate-agent.ts
const frame = StreamSocketFrame.safeParse(json);
...
const reduced = processor.reduce({ state: this.#streamProcessorState, event });
...
await processor.afterAppend({ event, state: this.#streamProcessorState, append: (...) => connection.send(...) });
```

And by daemon-side routing from logical path to execution harness:

```527:569:apps/daemon/server/routers/agents.ts
const { route } = await caller.getOrCreateAgent({ agentPath, ... });
...
const upstreamResponse = await fetch(destination, {
  method,
  headers: upstreamHeaders,
  body: method === "POST" ? JSON.stringify(await c.req.json()) : undefined,
});
```

So the system behaves like: **event arrives -> ensure agent route exists -> forward to harness -> harness executes and emits status/events**. I did not find a runtime planner-manager delegating to multiple LLM workers in one coordinated turn.

## 4. Tools & External Integrations

- **Cloudflare Workers AI models** via `deps.ai.run(...)` in assistant turn handling (`apps/agents/src/durable-objects/agent-processor.ts:86-101`).
- **Cloudflare Codemode dynamic worker execution** for user scripts (`DynamicWorkerExecutor.execute`) (`apps/agents/src/durable-objects/agent-processor.ts:60-79`).
- **MCP servers/tools**: DO registers MCP servers and wraps tools into codemode providers (`apps/agents/src/durable-objects/iterate-agent.ts:61-87`, `apps/agents/src/lib/mcp-tool-providers.ts:50-113`).
- **OpenAPI-as-tools**: converts OpenAPI operations into executable tools (used for Events API tooling) (`apps/agents/src/lib/openapi-tool-provider.ts:67-181`; wired in `apps/agents/src/durable-objects/iterate-agent.ts:48-56`).
- **OpenCode SDK integration** for session creation, async prompting, and lifecycle SSE (`apps/daemon/server/routers/opencode.ts:53-87`, `apps/daemon/server/routers/opencode.ts:142-205`).
- **GitHub API + GitHub App tokens** for PR context ingestion and routing signals to agents (`apps/os/backend/integrations/github/github-pr-agent.ts:161-183`, `apps/os/backend/integrations/github/github-pr-agent.ts:311-408`).
- **Database (Drizzle/SQLite in daemon context)** for agent/route/subscription persistence (`apps/daemon/server/routers/agents.ts:114-149`, `apps/daemon/server/routers/agents.ts:264-365`).
- **Machine runtime forwarding** to active sandbox machine/daemon endpoints (`apps/os/backend/integrations/github/github-pr-agent.ts:185-233`).

No vector DB/RAG store appears central in the inspected runtime agent path.

## 5. Notable Code Walkthrough

- `apps/agents/src/durable-objects/iterate-agent.ts:21-182` - Main Durable Object agent class. It initializes tool providers (OpenAPI + MCP), validates stream frames, updates persisted processor state, and emits append events back over websocket.
- `apps/agents/src/durable-objects/agent-processor.ts:26-110` - Core event processor implementing `reduce` (state projection) and `afterAppend` side effects (codemode script execution and model inference), effectively the decision engine.
- `apps/daemon/server/routers/agents.ts:249-603` - Agent control-plane router: get/create route atomically, fan-in concurrent creates, forward POST/GET traffic to resolved backend session, and stream upstream responses.
- `apps/daemon/server/routers/opencode.ts:35-213` - Concrete harness adapter to OpenCode sessions: translates Iterate prompt events into OpenCode prompts and listens to global event stream to update agent working status.
- `apps/os/backend/integrations/github/github-pr-agent.ts:311-408` - GitHub webhook-driven automation entrypoint that fetches PR context, decides whether to process, constructs workflow prompt, and forwards it into the target agent session.

## 6. Use-Case Mapping

The assigned use case **Workflow Automation** is accurate. The repo operationalizes automation by turning external triggers (especially GitHub PR/webhook signals) into structured prompts/events routed into persistent agent sessions, then feeding results/status back into the platform (`apps/os/backend/integrations/github/github-pr-agent.ts:377-388`, `apps/daemon/server/routers/agents.ts:527-569`). It is not primarily a code-generation-only framework or a RAG framework; instead it is an orchestration substrate for automating software/project workflows across machines, sessions, and tool integrations.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong event-contract-driven architecture with explicit schemas (`StreamSocketFrame`, `IterateEvent`) that reduces hidden coupling.
  - Durable routing/session layer handles concurrency and recovery (`inflightCreates`, pending route replacement).
  - Practical tool abstraction (OpenAPI->tools + MCP->tools) enables extensible capability injection without hardcoding each tool.
  - Integrates real operational triggers (GitHub webhooks, machine contexts), making automation directly useful in dev workflows.
  - Clear separation between control plane (routing/state) and execution harnesses (OpenCode, DO/codemode).

- **Limitations:**
  - Limited evidence of true multi-agent coordination (planner-worker/swarm) in runtime path; mostly single-session agent execution.
  - Some harnesses are stubs (`codex`, `claude`) and not production implementations (`apps/daemon/server/routers/codex.ts:6-24`, `apps/daemon/server/routers/claude.ts:6-24`).
  - Default assistant prompt logic is minimal and generic in processor (`"You are a helpful assistant..."`), with little built-in task decomposition.
  - Event protocol mismatch TODO noted in processor for codemode payload interoperability (`apps/agents/src/durable-objects/agent-processor.ts:22-25`).
  - Heavy dependence on surrounding infra (daemon, machine runtime, cloud services) raises setup complexity for isolated reuse.

- **Research relevance:**
  - Useful evidence for **event-driven agent orchestration** in production-like software operations.
  - Demonstrates how **agent sessions are treated as routable infrastructure resources** (path -> route -> harness).
  - Shows a concrete method for **tool unification** across MCP and OpenAPI in an agent runtime.
  - Provides a real example of **webhook-to-agent workflow automation** at repository/PR lifecycle boundaries.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
