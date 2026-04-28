---
repo_name: Alishahryar1/free-claude-code
url: "https://github.com/Alishahryar1/free-claude-code"
stars: 3515
forks: 682
contributors_count: 17
last_commit_date: "2026-04-23T00:34:00+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T12:30:37.289364+00:00"
model: auto
duration_s: 99.6
clone_size_kb: 2572
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`free-claude-code` is a FastAPI middleware that makes Anthropic-compatible clients (especially Claude Code CLI/extension) run against alternative providers (NVIDIA NIM, OpenRouter, DeepSeek, LM Studio, llama.cpp, Ollama) without changing client behavior. Users run the proxy server (`uvicorn server:app`) and point `ANTHROPIC_BASE_URL` to it, so Claude Code keeps speaking Anthropic API while the proxy handles routing, translation, and SSE normalization (`README.md:236-257`, `api/routes.py:79-103`). It also optionally runs a Discord/Telegram control plane that executes Claude CLI tasks remotely via a queueing/session system (`api/runtime.py:127-227`, `messaging/handler.py:98-240`). In practice, the user gets Claude-like tool-capable coding workflows on cheaper/free/local models, plus messaging-based task orchestration.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex; code search shows no framework imports, and orchestration is custom Python (`rg` over repo, no matches). The core architecture is a custom proxy + runtime composition: HTTP request entry (`api/routes.py`) -> model routing (`api/model_router.py`) -> provider adapter (`providers/*`) -> Anthropic-shaped SSE streaming (`api/services.py`, `core/anthropic/*`).

The “agentic” behavior is split across two layers. First, provider transports normalize tool-use and reasoning streams, including heuristic extraction of text-form tool calls (`providers/openai_compat.py:208-427`, `core/anthropic/tools.py:22-213`). Second, the messaging subsystem runs Claude CLI as subprocess sessions, parses streamed events, and maintains tree-structured task queues for threaded conversations (`cli/session.py:93-255`, `messaging/handler.py:311-447`, `messaging/trees/queue_manager.py:337-479`).

So intelligence mostly lives in: (a) model/provider routing logic, (b) SSE/tool-call transformation and guardrails, and (c) queue/state management around Claude CLI sessions, rather than a formal multi-agent planning graph.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker** (custom), with event-driven processing.

- A manager layer (`ClaudeMessageHandler` + `TreeQueueManager`) accepts incoming platform messages, builds/extends task trees, and dispatches node processing jobs (`messaging/handler.py:207-240`, `messaging/trees/queue_manager.py:456-479`).
- Worker layer is per-node Claude CLI execution (`cli_session.start_task(...)`) whose event stream is parsed and reflected into transcript/UI/state (`messaging/handler.py:393-447`, `messaging/node_event_pipeline.py:48-103`).

Control-flow excerpts:

```207:240:messaging/handler.py
# Create or extend tree
if parent_node_id and tree and status_msg_id:
    tree, _node = await self.tree_queue.add_to_tree(...)
...
# Enqueue for processing
was_queued = await self.tree_queue.enqueue(
    node_id=node_id,
    processor=self._process_node,
)
```

```316:330:messaging/trees/queue_manager.py
if tree.is_processing:
    tree.put_queue_unlocked(node_id)
    return True
else:
    tree.set_processing_state(node_id, True)
    node = tree.get_node(node_id)
    if node:
        tree.set_current_task(
            asyncio.create_task(self.process_node(tree, node, processor))
        )
```

## 4. Tools & External Integrations

- **Claude Code CLI subprocess execution** (primary execution tool): launched with `--output-format stream-json`, resume/fork support, workspace/dir scoping (`cli/session.py:123-167`).
- **LLM provider APIs**: NVIDIA NIM, OpenRouter, DeepSeek, LM Studio, llama.cpp, Ollama via provider registry/factories (`providers/registry.py:58-65`, `api/services.py:140-168`).
- **OpenAI SDK + HTTPX transport** for OpenAI-compatible streaming providers (`providers/openai_compat.py:14-17`, `providers/openai_compat.py:90-101`).
- **Discord and Telegram messaging platforms** as remote control interfaces for running tasks (`messaging/platforms/factory.py:55-103`, `messaging/platforms/discord.py:79-143`).
- **Voice transcription pipeline** (local Whisper or NVIDIA NIM path) wired into messaging adapters (`messaging/platforms/discord.py:128-221`).
- **Local web tools (`web_search` / `web_fetch`)** implemented in proxy for forced server-tool turns (`api/services.py:115-133`, `api/web_tools/streaming.py:40-207`).
- **Web egress/SSRF policy** for `web_fetch` target validation (`api/web_tools/egress.py:40-100`).

## 5. Notable Code Walkthrough

- `api/services.py:86-179` - Central request orchestrator: validates input, resolves model/provider, applies optimization shortcuts, optionally handles local web tools, then streams provider output as Anthropic SSE. This is the runtime hub.
- `providers/openai_compat.py:208-427` - Core streaming adapter that converts OpenAI-style deltas into Anthropic SSE, handles thinking blocks, native/heuristic tool calls, and provider error mapping; crucial interoperability layer.
- `cli/session.py:93-255` - Executes Claude CLI as a managed subprocess, injects proxy env vars, parses `stream-json` output, emits structured events, and handles cancellation/cleanup.
- `messaging/handler.py:98-240` - Inbound orchestration for Discord/Telegram messages: command filtering, tree linking for replies, queue placement, and status message lifecycle.
- `messaging/trees/queue_manager.py:337-619` - Tree-aware async scheduler managing per-conversation serialization, queued node execution, cancellation, and error propagation.

## 6. Use-Case Mapping

For the assigned **Browser / Terminal Use** label, the repository strongly matches the **terminal** half: it programmatically runs Claude Code CLI sessions, resumes/forks them, and streams tool/task events (`cli/session.py:123-149`, `messaging/handler.py:395-447`). It does **not** implement first-party browser automation frameworks (e.g., Playwright/Browserbase) in this codebase; browser-related behavior is mostly via generic web search/fetch server tools (`api/web_tools/streaming.py:40-207`). Overall, the stronger category from the provided list is **Workflow Automation**, because the main system automates end-to-end task execution/routing across providers and messaging channels rather than specializing in browser agents.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong protocol adaptation layer from multiple upstream APIs into Anthropic-compatible SSE (`providers/openai_compat.py:208-427`).
  - Robust operational controls: rate limiting, retries, scoped concurrency, and cleanup hooks (`providers/openai_compat.py:73-79`, `api/runtime.py:91-125`).
  - Practical remote orchestration via Discord/Telegram with queueing and persistent tree state (`api/runtime.py:176-253`, `messaging/trees/queue_manager.py:725-742`).
  - Defensive web-tool egress policy reduces SSRF risk (`api/web_tools/egress.py:40-94`).
  - Extensive tests/smokes structure for contracts and provider behavior (e.g., `tests/`, `smoke/`).

- **Limitations:**
  - No explicit multi-agent planner/router graph; orchestration is session/task management around a single CLI agent per node.
  - Heavy dependence on external Claude CLI semantics and event schema stability (`cli/session.py`, `messaging/event_parser.py`).
  - Provider-specific nuances still leak into transport branches (e.g., OpenAI-chat upstream constraints for server tools in `api/services.py:107-114`).
  - Runtime complexity (messaging + CLI + provider streaming) may increase operational debugging burden.
  - Browser automation is limited to web fetch/search abstractions; no rich browser control subsystem.

- **Research relevance:**
  - Useful evidence for **agent middleware/proxy architecture** that standardizes heterogeneous LLM backends under one protocol.
  - Illustrates **tool-call normalization and guardrailing** (heuristic parsing, forced Task behavior) in production-like pipelines (`core/anthropic/tools.py`, `providers/openai_compat.py:34-42`).
  - Demonstrates **queue/tree-based conversational orchestration** for asynchronous human-in-the-loop agent operations.
  - Relevant to studies on **reliable agent operations** (rate limiting, retries, cancellation propagation, session persistence).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
