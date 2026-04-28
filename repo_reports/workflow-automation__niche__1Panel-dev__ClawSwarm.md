---
repo_name: 1Panel-dev/ClawSwarm
url: "https://github.com/1Panel-dev/ClawSwarm"
stars: 186
forks: 11
contributors_count: 4
last_commit_date: "2026-04-21T08:17:02+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T17:50:25.945656+00:00"
model: auto
duration_s: 95.4
clone_size_kb: 3292
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`ClawSwarm` is a multi-component system that lets users run coordinated conversations among multiple OpenClaw agents, instead of a single assistant chat. In practice, users run the Dockerized platform (`scheduler-server` + `web-client`) and install the `channel` plugin into OpenClaw, then send direct or group messages that get routed to one or many agents. The scheduler persists conversations, dispatch records, and callback events, while the plugin executes agent turns and streams results back. The output users get is a managed multi-agent dialogue/workflow UI with status tracking, relay, and continuation across turns.

## 2. Agent Framework & Architecture

This repo does **not** use LangChain/LangGraph/CrewAI/AutoGen/LlamaIndex in code; it appears to be a **custom orchestration layer** over OpenClaw runtime APIs. The dependency files and imports show FastAPI/SQLAlchemy on the scheduler side and TypeScript plugin logic on the channel side, with no mainstream agent-framework imports (`scheduler-server/pyproject.toml:1-25`, `channel/package.json:1-45`, and no matches for those frameworks across source).

Architecture is split across:
- **`scheduler-server`**: authoritative state and workflow coordinator (conversations, dispatches, callback events, agent-dialogue relay logic).
- **`channel` plugin**: runtime bridge to OpenClaw agents; validates inbound webhooks, resolves routing (`DIRECT`, `GROUP_MENTION`, `GROUP_BROADCAST`), executes agent turns via runtime adapters, and emits callback events.
- **`web-client`**: operational UI for instances, groups, conversations, and agent dialogues.

The “intelligence” is mainly in:
1) **Routing + orchestration policy** (`channel/src/core/routing/resolveRoute.ts:78-135`, `channel/src/flows/dispatch/dispatchGroup.ts:33-86`),  
2) **Stateful turn relay logic** for two-agent dialogues (`scheduler-server/src/services/agent_dialogue_runner.py:51-117`), and  
3) **Prompt/context packaging** before each dispatch (`scheduler-server/src/services/conversation_dispatch_service.py:171-197`, `agent_dialogue_runner.py:156-173`).

## 3. Orchestration Pattern

Closest match: **event-driven + swarm-style fan-out orchestration** (with a **sequential relay subpattern** for pair dialogues).

- Event-driven: inbound messages are ACKed quickly, then dispatched asynchronously (`setImmediate`) to routing/execution (`channel/src/http/inbound.ts:137-199`).
- Swarm fan-out: group messages are expanded into per-agent tasks and executed concurrently with global/per-agent concurrency limits (`channel/src/flows/dispatch/dispatchGroup.ts:49-79`, `groupQueue.ts:59-91`).
- Sequential relay: in `agent_dialogue` mode, each `reply.final` triggers the next participant turn (`scheduler-server/src/services/callback_event_service.py:131-139`, `agent_dialogue_runner.py:95-117`).

Example control-flow excerpt:
```33:60:channel/src/flows/dispatch/dispatchGroup.ts
const queue = createGroupDispatchQueue(accountConfig);
const targets = prepareGroupDispatchTargets({ inbound, agentIds, routeKind });
const tasks = targets.map(async ({ agentId, sessionKey }) => {
  return queue.run({
    accountId, agentId, sessionKey,
    task: async () => await dispatchDirect({ ... })
  });
});
const results = await Promise.all(tasks);
```

And event-triggered continuation:
```131:139:scheduler-server/src/services/callback_event_service.py
if event_type == "reply.final" and agent_message:
    dialogue = db.scalar(select(AgentDialogue).where(AgentDialogue.conversation_id == dispatch.conversation_id))
    if dialogue:
        await continue_agent_dialogue_after_reply(
            db=db, dialogue=dialogue, dispatch=dispatch, reply_message=agent_message,
        )
```

## 4. Tools & External Integrations

- **OpenClaw runtime (agent execution)**: adapter abstraction chooses `plugin_runtime` vs `chat_completions` transport (`channel/src/openclaw/runtime/adapters.ts:34-73`, `chatCompletionsAdapter.ts:17-77`).
- **OpenClaw CLI (agent management/workspace)**: create/list/update agent profiles via CLI calls (`channel/src/openclaw/agents/manageAgents.ts:79-134`).
- **Custom callback API to scheduler-server**: plugin posts `run.accepted`, `reply.chunk`, `reply.final`, `run.error` events with HMAC headers (`channel/src/flows/callback/client.ts:47-81`), consumed by FastAPI callback routes (`scheduler-server/src/api/routes/callbacks.py:50-70`).
- **Document-reading tool exposed to agents**: `clawswarm_read_document` tool fetches `clawswarm://` docs via scheduler API (`channel/src/openclaw/tools/readDocumentTool.ts:24-53`, `channel/src/flows/documents/readDocument.ts:31-64`).
- **Database persistence**: SQLAlchemy models/session used for conversations, message dispatches, callback events (`scheduler-server/src/services/callback_event_service.py:41-77`).
- **Redis optional idempotency store**: configured in channel account schema (`channel/src/config/schema.ts:70-77`), with `ioredis` dependency (`channel/package.json:34-38`).
- **Webchat mirror integration**: OpenClaw web UI transcript messages mirrored into scheduler conversation stream (`scheduler-server/src/services/webchat_mirror_service.py:25-105`).

No browser automation stack (Playwright), vector DB, or RAG pipeline is wired here.

## 5. Notable Code Walkthrough

- `channel/src/http/inbound.ts:45-200` - Main webhook entrypoint: verifies signatures, validates payload, resolves route, ACKs immediately, and schedules asynchronous dispatch. This is the core runtime ingress for all agent work.
- `channel/src/flows/dispatch/dispatchGroup.ts:33-86` - Multi-agent fan-out executor for group messages; creates dispatch targets and runs each through bounded queueing before final status aggregation.
- `channel/src/flows/dispatch/groupQueue.ts:59-91` - Concurrency-control backbone (global semaphore + per-agent semaphore + keyed ordering), critical for stable multi-agent execution under load.
- `scheduler-server/src/services/callback_event_service.py:20-149` - Applies runtime callback events to persistent dispatch/message state and triggers next-turn relay in agent-dialogue mode.
- `scheduler-server/src/services/agent_dialogue_runner.py:120-179` - Builds dialogue context and dispatch payload for one agent turn, then forwards through channel client; this is where pair-dialogue automation is advanced.

## 6. Use-Case Mapping

The assigned category **`Workflow Automation` is correct**. The system automates a repeatable workflow loop: accept incoming message -> route to appropriate agent set -> execute agent turn(s) -> persist/stream callbacks -> optionally chain to next agent automatically. Group dispatch and relay dialogues are both automation primitives rather than ad-hoc chat features (`channel/src/core/routing/resolveRoute.ts:78-135`, `dispatchGroup.ts:49-85`, `agent_dialogue_runner.py:51-117`). It is not primarily code generation, RAG, or simulation; it is an orchestration workflow layer for multi-agent task execution and coordination.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear separation of control-plane (`scheduler-server`) and execution-plane (`channel`) responsibilities.
  - Explicit runtime routing modes (`DIRECT`, `GROUP_MENTION`, `GROUP_BROADCAST`) with deterministic branching.
  - Practical production controls: signature verification, idempotency, retry configuration, and concurrency semaphores.
  - Supports both parallel swarm fan-out and sequential two-agent relay in one system.
  - Includes tool integration (`clawswarm_read_document`) and session-aware context packaging.

- **Limitations:**
  - Coordination strategy is mostly rule-based routing; no advanced planner/critic/meta-reasoner policies.
  - Heavy reliance on OpenClaw-specific runtime/CLI contracts reduces portability.
  - Limited built-in evaluation/benchmarking for multi-agent quality (mostly operational tests).
  - Group context prompt construction is handcrafted strings; may be brittle for complex long-horizon tasks.
  - No explicit conflict-resolution/debate scoring mechanism among agent outputs.

- **Research relevance:**
  - Useful evidence of a real-world, event-driven multi-agent orchestration implementation integrated with existing agent runtime infrastructure.
  - Demonstrates hybrid coordination: bounded parallel fan-out plus callback-triggered sequential relay.
  - Shows engineering patterns for safe multi-agent operations (idempotency, backpressure, signed callbacks).
  - Illustrates how “swarm chat” systems operationalize per-agent session isolation and stateful turn continuation.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
