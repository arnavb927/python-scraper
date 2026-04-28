---
repo_name: ruvnet/RuView
url: "https://github.com/ruvnet/RuView"
stars: 49427
forks: 6558
contributors_count: 13
last_commit_date: "2026-04-20T18:29:15+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T09:25:06.647367+00:00"
model: auto
duration_s: 113.1
clone_size_kb: 157096
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`ruvnet/RuView` is primarily a WiFi sensing platform (ESP32 CSI + Rust/Python/JS pipelines) for pose estimation, presence, and vitals, but this repo also embeds a substantial **agentic development/operations layer** under `.claude/` and `.claude-flow/`. In practice, users run sensing/simulation CLIs like `scripts/qemu_swarm.py` and `scripts/qemu-cli.sh` for multi-node ESP32/QEMU swarm testing, while the agent layer automates coding workflows (routing tasks, cross-agent messaging, consensus, memory, and pattern learning). The LLM-agent subsystem is not the RF inference runtime itself; it is a coordination shell around developer tasks and automation. So the repository solves two problems at once: RF simulation/sensing execution and AI-assisted workflow orchestration.

## 2. Agent Framework & Architecture

This repo does **not** use LangChain/LangGraph/CrewAI/AutoGen imports in runtime code. The agent stack is a **custom orchestration layer** built around **Claude Flow / agentic-flow tooling** plus local scripts/hooks (`.claude/settings.json:2-272`, `.mcp.json:2-21`, `.claude/helpers/hook-handler.cjs:45-67`).

Architecture-wise, agent behavior is split across:
- **Hook entrypoint/router**: `hook-handler.cjs` dispatches events like `route`, `pre-task`, `post-task`, `session-restore`, integrating router + memory/intelligence (`.claude/helpers/hook-handler.cjs:56-217`).
- **Agent routing**: lightweight keyword routing picks role-specific agents (`coder`, `tester`, `reviewer`, etc.) in `router.js` (`.claude/helpers/router.js:7-53`).
- **Swarm coordination plane**: messaging, handoffs, consensus, pattern broadcast in `swarm-hooks.sh` and `swarm-comms.sh` (`.claude/helpers/swarm-hooks.sh:92-165`, `276-390`; `.claude/helpers/swarm-comms.sh:30-79`, `207-248`).
- **Learning/memory plane**: PageRank-ranked memory graph (`intelligence.cjs`) and persistent vector-like pattern storage with HNSW + SQLite (`learning-service.mjs`) (`.claude/helpers/intelligence.cjs:304-405`, `411-466`; `.claude/helpers/learning-service.mjs:171-229`, `570-714`).

The “intelligence” lives mainly in scripted heuristics + retrieval/ranking + feedback loops, not in prompt templates checked into core app code.

## 3. Orchestration Pattern

Closest match: **hybrid swarm + event-driven workflow automation** (with some hierarchical routing).

Control starts from hook events, routes to an agent type, then uses file-backed swarm channels (messages/consensus/handoffs). Example routing path:

`hook-handler.cjs` (`.claude/helpers/hook-handler.cjs:56-67`):
```text
const handlers = {
  'route': () => {
    if (intelligence && intelligence.getContext) { ... }
    if (router && router.routeTask) {
      const result = router.routeTask(prompt);
```

`router.js` (`.claude/helpers/router.js:32-43`):
```text
for (const [pattern, agent] of Object.entries(TASK_PATTERNS)) {
  const regex = new RegExp(pattern, 'i');
  if (regex.test(taskLower)) {
    return { agent, confidence: 0.8, reason: `Matched pattern: ${pattern}` };
```

Peer coordination is swarm-like (broadcast/consensus/handoff), e.g. `swarm-hooks.sh` (`.claude/helpers/swarm-hooks.sh:311-316`, `346-383`) broadcasts consensus requests and resolves votes into a winning option/confidence.

## 4. Tools & External Integrations

- **MCP server (`claude-flow`)**: wired in `.mcp.json` with `npx @claude-flow/cli@latest mcp start` (`.mcp.json:3-20`).
- **Claude Code hook integration**: lifecycle hooks call helper scripts for routing/memory/session sync (`.claude/settings.json:2-117`).
- **Local filesystem as coordination bus**: swarm messages/patterns/consensus/handoffs persisted as JSON files (`.claude/helpers/swarm-hooks.sh:19-25`, `101-114`, `295-307`, `455-467`; `.claude/helpers/swarm-comms.sh:9-12`, `41-43`).
- **SQLite (`better-sqlite3`) for persistent learning state**: pattern DB and metrics (`.claude/helpers/learning-service.mjs:25`, `81-165`, `591-603`).
- **Embedding backend**: optional `agentic-flow` ONNX embedder, fallback hash embeddings (`.claude/helpers/learning-service.mjs:463-488`, `491-563`).
- **Shell ecosystem dependencies**: `jq`, `bc`, `npx`, and process spawning used by swarm scripts (`.claude/helpers/swarm-hooks.sh:60-64`, `233-234`; `.claude/helpers/swarm-comms.sh:59-61`, `171-172`).
- **Non-agent simulation tooling**: QEMU/ESP32 swarm orchestration (`scripts/qemu_swarm.py:1-1145`, `scripts/qemu-cli.sh:158-172`).

## 5. Notable Code Walkthrough

- `.claude/helpers/hook-handler.cjs:56-217`  
  Central dispatcher from Claude hook events into routing, session lifecycle, and intelligence feedback. This is the practical “entrypoint” for agent automation behavior.

- `.claude/helpers/swarm-hooks.sh:92-165, 276-390, 424-555`  
  Implements agent-to-agent messaging, consensus protocol, and structured task handoff with JSON context payloads; this is the strongest evidence of coordinated multi-agent behavior.

- `.claude/helpers/intelligence.cjs:304-405, 411-466, 527-665`  
  Builds a memory graph, computes PageRank, retrieves top context for new prompts, and consolidates learned patterns across sessions.

- `.claude/helpers/learning-service.mjs:171-229, 570-714, 732-782`  
  Persistent learning backend with HNSW-like index + SQLite, pattern retrieval, usage tracking, and short-term→long-term promotion.

- `scripts/qemu_swarm.py:751-917`  
  Not LLM-agent code; orchestrates ESP32/QEMU node simulation lifecycle. Important because it shows the repo’s separate simulation core vs. AI workflow layer.

## 6. Use-Case Mapping

The assigned primary use case (`Simulation`) is valid for the **main product runtime** (`qemu_swarm.py`, `swarm_health.py`, firmware/QEMU orchestration). However, the LLM-agent implementation in this repo is mostly for **developer/task orchestration** (routing, swarm messaging, consensus, memory, hook-driven automation), not RF simulation inference itself. For the specific “multi-agent systems” lens, a better label is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent primitives (routing, broadcast, consensus, handoff) implemented concretely in scripts (`.claude/helpers/swarm-hooks.sh`).
  - Event-driven integration into real developer workflow via hook lifecycle (`.claude/settings.json`, `hook-handler.cjs`).
  - Persistent learning loop (retrieval + confidence updates + consolidation) with explicit data model (`intelligence.cjs`, `learning-service.mjs`).
  - Practical hybrid memory stack (file caches + SQLite + vector-style index) rather than purely stateless prompts.
  - Coexists with a real non-LLM simulation system, enabling mixed cyber-physical + agentic workflows.

- **Limitations:**
  - Routing is mostly keyword heuristics (`router.js`) rather than model-based planning/policy.
  - Swarm coordination relies on filesystem JSON/mailboxes; can be brittle under concurrency and process crashes.
  - No evidence of strong formal guarantees for consensus/handoff correctness (best-effort scripting).
  - Agent framework coupling is mostly to Claude tooling; portability to other runtimes appears limited.
  - Several agent capabilities are configured/documented, but not all are clearly tied to production runtime paths.

- **Research relevance:**
  - Example of **event-driven MAS orchestration** embedded in dev tooling rather than end-user chat products.
  - Useful case for studying **lightweight, script-native swarm coordination** (message queues, handoffs, consensus) without heavyweight frameworks.
  - Demonstrates **memory-ranked agent context injection** (PageRank + feedback) in practical workflows.
  - Illustrates boundary between domain simulation code and agentic workflow automation in a single repo.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
