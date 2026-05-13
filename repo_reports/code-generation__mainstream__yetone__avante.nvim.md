---
repo_name: yetone/avante.nvim
url: "https://github.com/yetone/avante.nvim"
stars: 17800
forks: 814
contributors_count: 267
last_commit_date: "2026-03-30T03:20:49+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:49:31.943809+00:00"
model: auto
duration_s: 170.0
clone_size_kb: 2187
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`yetone/avante.nvim` is a Neovim plugin that embeds an agentic coding assistant directly into the editor sidebar and command workflow (for example via `:AvanteAsk`, `:AvanteChat`, and `:AvanteEdit` in `plugin/avante.lua:83-136`). A user runs the plugin inside Neovim, asks for coding tasks, and the system streams model output plus tool activity while reading/editing project files and optionally running commands. The core value is IDE-native automation: code understanding, patching, diagnostics, git actions, and optional retrieval/search, without leaving Neovim. It also supports both direct LLM providers and ACP-compatible external coding agents (e.g., Claude Code, Codex, Gemini CLI) configured in `lua/avante/config.lua:248-291`.

## 2. Agent Framework & Architecture

This repo uses **custom agent orchestration**, not LangGraph/LangChain/AutoGen/CrewAI as a runtime dependency for the main agent loop. The control plane is Lua code in `lua/avante/llm.lua`, where `M._stream` and `M.agent_loop` manage prompt construction, tool-call parsing, tool execution, and iterative re-entry into the model (`lua/avante/llm.lua:185-256`, `1751-2038`). The “intelligence” lives in prompt templates (`lua/avante/templates/agentic.avanterules`) plus tool schema/constraints (`lua/avante/llm_tools/init.lua`).

The architecture is a **tool-using primary coding agent** with optional recursive sub-agents. The primary agent is given a large toolset (`M._tools`) including file edits, grep/glob, bash, todos, web fetch/search, git, RAG retrieval, and `dispatch_agent` (`lua/avante/llm_tools/init.lua:647-1249`). `dispatch_agent` launches another `agent_loop` with a reduced toolset (`ls`, `grep`, `glob`, `view`, `attempt_completion`) for delegated search/research tasks (`lua/avante/llm_tools/dispatch_agent.lua:74-82`, `209-275`).

Separately, ACP mode integrates with external “agent runtimes” over JSON-RPC/stdio (`lua/avante/libs/acp_client.lua:340-498`, `730-817`) and relays their plan/tool/message updates into Avante’s UI and history (`lua/avante/llm.lua:916-1748`). So there are two runtime paths: internal custom agent loop, and external ACP agent orchestration.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with iterative tool loop**.

- The manager loop repeatedly invokes model -> executes pending tools -> appends tool results -> re-enters model until completion:
`lua/avante/llm.lua:1811-1848`, `1976-1979`.
- A dedicated `dispatch_agent` tool creates subordinate agents with narrower capabilities, i.e., manager delegates scoped tasks to workers:
`lua/avante/llm_tools/dispatch_agent.lua:74-82`, `209-275`.

Example control-flow excerpt:

```lua
1818:          if tool_use_index > #tool_uses then
1836:          local new_opts = vim.tbl_deep_extend("force", opts, {
1837:            history_messages = opts.get_history_messages and opts.get_history_messages() or {},
1847:          if not streaming_tool_use then M._stream(new_opts) end
1976:      if stop_opts.reason == "tool_use" then
1978:        return handle_next_tool_use(pending_tools, pending_tool_use_messages, 1, {}, stop_opts.streaming_tool_use)
```
(`lua/avante/llm.lua:1818-1848`, `1976-1979`)

Delegation excerpt:

```lua
74:local function get_available_tools()
75:  return {
76:    require("avante.llm_tools.ls"),
77:    require("avante.llm_tools.grep"),
78:    require("avante.llm_tools.glob"),
79:    require("avante.llm_tools.view"),
80:    require("avante.llm_tools.attempt_completion"),
81:  }
```
(`lua/avante/llm_tools/dispatch_agent.lua:74-81`)

## 4. Tools & External Integrations

- **LLM providers (OpenAI/Anthropic/Copilot/Gemini/etc.)**: configured and normalized in `lua/avante/config.lua:295-516`, consumed by provider adapters and `llm.lua`.
- **ACP external agent runtimes** (Claude Code, Codex, Gemini CLI, Goose, etc.): provider entries in `lua/avante/config.lua:248-291`; JSON-RPC client/transport in `lua/avante/libs/acp_client.lua:340-531`; session/prompt flow in `lua/avante/llm.lua:1341-1748`.
- **Filesystem/code-edit tools**: `view`, `str_replace`, `write_to_file`, `insert`, `edit_file`, path operations in `lua/avante/llm_tools/init.lua:34-217`, `851-1132`.
- **Shell/terminal execution**: `bash` tool with permission checks and restrictions in `lua/avante/llm_tools/bash.lua:11-263`.
- **Git automation**: `git_diff` and `git_commit` tools in `lua/avante/llm_tools/init.lua:383-521`.
- **Web search and fetch**: multi-provider web search (`tavily`, `serpapi`, `google`, etc.) in `lua/avante/llm_tools/init.lua:219-371`; URL-to-markdown fetch in `374-381`.
- **RAG service integration**: Lua client/service lifecycle in `lua/avante/rag_service.lua:39-448`; `rag_search` tool in `lua/avante/llm_tools/init.lua:523-545`.
- **RAG backend stack**: FastAPI + LlamaIndex + ChromaDB in `py/rag-service/src/main.py:23-52`, with `/api/v1/retrieve` and indexing endpoints (`1026-1410`).
- **LSP symbol/definition lookups**: `read_definitions` tool wired through Neovim LSP in `lua/avante/llm_tools/init.lua:1193-1247`.
- **MCP servers via ACP sessions**: passed when creating ACP session (`create_session(..., mcp_servers, ...)`) in `lua/avante/llm.lua:1343-1346` and `lua/avante/libs/acp_client.lua:817-823`.

## 5. Notable Code Walkthrough

- `lua/avante/llm.lua:1751-2038` - Core runtime loop: prompt generation, stream handling, tool-use detection, execution, result reinjection, retries/rate-limit handling. This is the main orchestrator for internal agentic mode.
- `lua/avante/llm_tools/init.lua:647-1249` - Declares the canonical tool registry and implementations, including `dispatch_agent`, editing, git, web, diagnostics, RAG, and completion semantics.
- `lua/avante/llm_tools/dispatch_agent.lua:12-275` - Implements sub-agent delegation by spawning a nested `agent_loop` with restricted tools, making runtime multi-agent behavior explicit.
- `lua/avante/libs/acp_client.lua:340-1016` - ACP protocol client (stdio JSON-RPC), session lifecycle, prompt submission, permission and FS callback plumbing for external agent engines.
- `py/rag-service/src/main.py:1026-1299` - Retrieval/indexing service that powers `rag_search`, including document filtering, query execution, and source-grounded responses.

## 6. Use-Case Mapping

This repo does support **Code Generation**, but the observed center of gravity is broader **Workflow Automation** for coding tasks. The agent loop manages multi-step execution (planning TODOs, searching code, editing files, running commands, committing, and completion signaling) rather than only producing code text (`lua/avante/templates/agentic.avanterules:91-121`, `lua/avante/llm.lua:1811-1979`). The optional `dispatch_agent` sub-agents and ACP external runtimes further emphasize orchestrated developer workflows over pure code synthesis. So the upstream “Code Generation” label is partially correct, but “Workflow Automation” is a better final category.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong end-to-end in-editor agent loop with iterative tool grounding (`lua/avante/llm.lua`).
  - Explicit delegated sub-agent mechanism (`dispatch_agent`) enabling hierarchical decomposition.
  - Broad practical tool surface (edit/search/git/shell/web/RAG/LSP) in one runtime (`llm_tools/init.lua`).
  - Supports both built-in orchestration and external ACP agents, making it interoperable.
  - Good operational concerns: cancellation, rate-limit backoff, memory summarization, session recovery.

- **Limitations:**
  - No explicit graph/state-machine framework; orchestration logic is complex and hand-rolled in a large file.
  - Multi-agent coordination is shallow (manager + delegated search workers), not rich peer-to-peer cooperation.
  - Tool safety relies heavily on prompt instructions + runtime checks; policy completeness may vary by tool.
  - ACP behavior depends on external agent implementations, so determinism/reproducibility can vary.
  - RAG service is separate and operationally heavier (Docker/Nix/FastAPI/Chroma), increasing setup complexity.

- **Research relevance:**
  - Real-world evidence of **hierarchical LLM agent orchestration in developer tooling**.
  - Example of **hybrid local orchestrator + external agent protocol (ACP)** integration.
  - Demonstrates **tool-mediated iterative control loops** with completion gates and user-permission hooks.
  - Useful case study for **agent UX in IDEs** (streaming thoughts/tools/todos, human-in-the-loop approvals).

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
