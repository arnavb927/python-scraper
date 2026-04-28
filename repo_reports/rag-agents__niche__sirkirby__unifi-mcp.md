---
repo_name: sirkirby/unifi-mcp
url: "https://github.com/sirkirby/unifi-mcp"
stars: 267
forks: 50
contributors_count: 13
last_commit_date: "2026-04-14T16:02:56+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:38:53.881717+00:00"
model: auto
duration_s: 82.0
clone_size_kb: 8009
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`unifi-mcp` is a Python monorepo that implements MCP servers for UniFi Network, Protect, and Access so an external AI assistant (or any MCP client) can operate UniFi controllers through structured tools. In practice, users run server packages like `unifi-network-mcp` (stdio/HTTP transport) and then connect from a client such as Claude Code/Desktop (`README.md:35-65`, `apps/network/src/unifi_network_mcp/main.py:46-90`). The servers expose hundreds of domain tools (clients, firewall, cameras, doors, etc.) with a consistent response contract and safety model (preview-then-confirm for mutations). The repo also includes a relay sidecar that forwards tool calls from cloud workers to local MCP servers, enabling cross-location/cloud execution without exposing local ports (`packages/unifi-mcp-relay/src/unifi_mcp_relay/main.py:21-61`).

## 2. Agent Framework & Architecture

This repo does **not** implement an internal LLM agent framework (no LangChain/LangGraph/CrewAI/AutoGen/LlamaIndex imports found in source). Instead, it is MCP infrastructure: FastMCP servers plus tool wrappers, manager classes, and transport/permission utilities (`apps/network/src/unifi_network_mcp/runtime.py:25-33`, `apps/network/src/unifi_network_mcp/main.py:64-89`, `packages/unifi-mcp-shared/src/unifi_mcp_shared/tool_registration.py:25-45`).

The “intelligence” inside this codebase is mostly deterministic orchestration and policy/safety logic: tool discovery, lazy/eager registration modes, permission gates, and mutation confirmation workflows. Tool functions are thin async adapters over manager methods and UniFi API calls, not agent-planner loops (`apps/network/src/unifi_network_mcp/tools/clients.py:21-53`, `docs/ARCHITECTURE.md:129-148`).

There are **agent-facing assets** in `plugins/*/skills/*` (prompt/instruction files for Claude plugin usage), but they are not autonomous multi-agent runtime code in this repository; they guide an external assistant on which MCP tools to call (`plugins/cross-product/skills/security-patrol/SKILL.md:12-21`).

## 3. Orchestration Pattern

Closest match: **event-driven service orchestration** (MCP server + dispatcher), not multi-agent orchestration.

Control flow is request/dispatch based: incoming tool calls are routed through registered decorators to specific tool handlers, which delegate to manager classes. Registration mode (`meta_only`/`lazy`/`eager`) controls how tools are exposed, but there is no planner-worker graph.

```46:75:apps/network/src/unifi_network_mcp/main.py
# ---- Register tools ----
await register_tools_for_mode(
    mode=UNIFI_TOOL_REGISTRATION_MODE,
    server=server,
    original_tool_decorator=_original_tool_decorator,
    ...
    tool_module_map=TOOL_MODULE_MAP,
    setup_lazy_loading=setup_lazy_loading,
)
```

Meta-tools provide a deterministic execution gateway (`*_execute`, `*_batch`) that forwards calls to selected tools:

```175:183:packages/unifi-mcp-shared/src/unifi_mcp_shared/meta_tools.py
async def execute_handler(tool: str, arguments: dict = None) -> dict:
    if arguments is None:
        arguments = {}
    try:
        result = await server.call_tool(tool, arguments)
        return result
```

## 4. Tools & External Integrations

- **MCP server runtime (FastMCP):** core tool exposure and transport handling via `mcp.server.fastmcp.FastMCP` (`apps/network/src/unifi_network_mcp/runtime.py:25-27`, `runtime.py:95-120`).
- **UniFi controller APIs:** accessed through manager/connection layers (`unifi-core`, app managers), e.g., client/firewall/device operations (`docs/ARCHITECTURE.md:133-141`, `apps/network/src/unifi_network_mcp/tools/clients.py:35-53`).
- **MCP protocol meta-tools:** discovery and execution tools (`unifi_tool_index`, `unifi_execute`, `unifi_batch`) for external assistants (`packages/unifi-mcp-shared/src/unifi_mcp_shared/meta_tools.py:34-52`, `meta_tools.py:157-231`).
- **Cloud relay (WebSocket + MCP HTTP):** sidecar discovers tools from local servers and forwards calls to a Cloudflare Worker path (`README.md:24-31`, `packages/unifi-mcp-relay/src/unifi_mcp_relay/main.py:36-61`, `forwarder.py:74-92`).
- **Plugin skill scripts (deterministic automation):** Python scripts call MCP tools directly (parallel tool calls, audits), but still no embedded LLM model runtime (`plugins/unifi-network/skills/firewall-auditor/scripts/run-audit.py:711-756`, `skills/_shared/mcp_client.py:47-91`).
- **External LLM frameworks/vector DB/browser automation:** none wired in this codebase.

## 5. Notable Code Walkthrough

- `apps/network/src/unifi_network_mcp/main.py:46-90` - Main server lifecycle: initializes UniFi connection, registers tools by mode, and starts stdio/HTTP transports; this is the runtime entrypoint for Network MCP.
- `apps/network/src/unifi_network_mcp/runtime.py:94-135` - Creates singleton FastMCP server and decorator wrapping; central infrastructure that all tool modules depend on.
- `packages/unifi-mcp-shared/src/unifi_mcp_shared/meta_tools.py:34-105` - Defines tool-index/discovery behavior that external agents rely on to inspect available capabilities before invoking domain tools.
- `apps/network/src/unifi_network_mcp/tools/clients.py:21-53` - Representative tool wrapper pattern: validates args, calls manager, catches exceptions, and returns structured `success/error` payloads.
- `packages/unifi-mcp-relay/src/unifi_mcp_relay/main.py:110-145` - Relay orchestrator that periodically rediscovers catalogs and forwards tool calls, enabling cloud-to-local MCP workflows.

## 6. Use-Case Mapping

The assigned label **“RAG + Agents”** looks overstated for this repository itself. The code does not implement retrieval pipelines, vector search, or in-repo LLM-agent teams; it implements an MCP tool ecosystem that external assistants can use for **operational automation** across UniFi systems. Even the “skills” are instruction templates and deterministic scripts around MCP tool invocation, not internal agent graphs (`plugins/cross-product/skills/security-patrol/SKILL.md:14-20`, `skills/_shared/mcp_client.py:30-49`).  
Better fit: **Workflow Automation** (tool-driven infrastructure operations via external AI clients).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong modular architecture with clear layering (tools -> managers -> connection) and shared patterns across three app servers (`docs/ARCHITECTURE.md:118-149`).
  - Safety-oriented mutation model (preview/confirm, permission gating) suitable for production automation.
  - Scalable tool exposure strategy (`meta_only`/`lazy`/`eager`) that balances context size and capability breadth (`tool_registration.py:92-147`).
  - Relay sidecar cleanly decouples cloud access from local controller hosting (`unifi_mcp_relay/main.py:36-61`).
  - Extensive domain coverage (network/protect/access) and practical automation scripts.

- **Limitations:**
  - No native multi-agent runtime, planner, or LLM policy module inside repo (agent behavior is delegated to external clients).
  - No built-in RAG stack (no embeddings/vector DB/document retriever integration).
  - “Agent skills” are largely static prompt/docs artifacts; runtime enforcement of those workflows is limited.
  - Heavy operational dependence on external UniFi controller availability and client-side LLM quality.
  - Cross-product intelligence is mostly composition of existing tool outputs, not learned reasoning components.

- **Research relevance:**
  - Good evidence for **agent tool substrate design**: how to expose secure, typed, discoverable operational tools over MCP.
  - Useful case for **safety controls in AI operations** (permission gates + confirm-before-mutate) in real infrastructure domains.
  - Demonstrates **cloud-local relay architecture** for agent tool access without direct network exposure.
  - Less suitable as evidence of multi-agent coordination algorithms or emergent agent collaboration.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
