---
repo_name: plasma-umass/coz
url: "https://github.com/plasma-umass/coz"
stars: 4485
forks: 169
contributors_count: 43
last_commit_date: "2026-04-18T13:55:37+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T13:26:18.825195+00:00"
model: auto
duration_s: 63.9
clone_size_kb: 26664
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`plasma-umass/coz` is primarily a native-code causal profiler (C/C++/Rust), but in this version it also includes optional LLM-assisted workflows. Users run `coz run --- <program>` to collect profile data, then `coz plot` to launch a local viewer that can now request AI optimization suggestions for selected hot lines. There is also a CLI command, `coz suggest-points`, that uses an LLM tool-use loop to propose and optionally insert `COZ_PROGRESS` / `COZ_BEGIN` / `COZ_END` instrumentation into source code. So the repo solves both profiling and “assistive automation around profiling setup/interpretation,” not general autonomous coding.

## 2. Agent Framework & Architecture

This repo does **not** use LangChain, LangGraph, CrewAI, AutoGen, or LlamaIndex. There are no imports of those frameworks, and the agent behavior is implemented as **custom tool-calling loops** against provider APIs (`Anthropic`, `OpenAI`, `Bedrock`, `Ollama`) directly in the `coz` Python script (`coz:1616-1904`, `coz:2192-2255`).

The main agentic path is `coz suggest-points`: a single planning agent receives a system prompt plus a small toolset (`list_files`, `read_file`, `grep`, `propose_point`) and iterates until it stops requesting tools (`coz:1359-1442`, `coz:1643-1668`, `coz:1711-1749`, `coz:1765-1840`, `coz:1867-1904`). Intelligence lives in prompt instructions plus tool-call loop orchestration; execution is deterministic Python handlers over local files (`coz:1474-1608`).

A second, lighter LLM integration exists in the web viewer: clicking AI optimize sends source context and speedup curve data to `/optimize`, which streams one model response back to UI (`coz:988-1135`, `viewer/ts/profile.ts:646-761`). That path is single-request inference, not multi-agent coordination.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker), single-agent tool-use loop**.  
The Python runtime acts as manager/orchestrator; one LLM “worker” decides which tool to call next, and the manager executes calls and feeds results back.

Example control flow in Anthropic loop (`coz:1643-1668`):

```178:187:coz
for iteration in range(_SUGGEST_MAX_ITERATIONS):
  resp = _anthropic_tool_request(key, model, system_prompt, messages, tools)
  ...
  tool_uses = [b for b in content if isinstance(b, dict) and b.get('type') == 'tool_use']
  if not tool_uses:
    return
  ...
  result = handle_tool(name, input_)
```

Equivalent pattern for OpenAI tool calls (`coz:1711-1747`):

```1715:1729:coz
for iteration in range(_SUGGEST_MAX_ITERATIONS):
  resp = _openai_tool_request(key, model, system_prompt, messages, tools)
  ...
  tool_calls = msg.get('tool_calls') or []
  ...
  if not tool_calls:
    return
```

So it is not graph/swarm/event-driven MAS; it is a bounded sequential tool-calling controller around one model instance.

## 4. Tools & External Integrations

- **LLM providers (Anthropic/OpenAI/Bedrock/Ollama)**: wired in CLI + viewer backend (`coz:1144-1290`, `coz:2198-2255`, `coz:755-932`, `coz:988-1135`).
- **Local source-tree tools for agent**: `list_files`, `read_file`, regex `grep`, `propose_point` for instrumentation plans (`coz:1381-1442`, `coz:1474-1608`).
- **HTTP viewer server**: local threaded server exposes `/llm-config`, `/source-snippet`, model-list endpoints, `/optimize` streaming endpoint (`coz:696-943`, `coz:988-1137`, `coz:1291-1337`).
- **Browser UI integration**: frontend calls `/optimize` stream, shows model/provider controls, caches models, and renders streaming results (`viewer/ts/profile.ts:175-196`, `viewer/ts/profile.ts:315-438`, `viewer/ts/profile.ts:646-761`, `viewer/ts/profile.ts:1401-1542`).
- **AWS Bedrock SDK**: optional `boto3` integration for model listing and inferencing (`coz:653-657`, `coz:872-925`, `coz:1249-1289`, `pyproject.toml:11-13`).

No MCP servers, vector DB, browser automation frameworks (Playwright), or RAG index pipeline are present.

## 5. Notable Code Walkthrough

- `coz:1345-2267`  
  Implements `coz suggest-points`, including prompt design, tool schema, provider-specific agent loops, proposal validation, diff rendering, and optional apply-to-files. This is the core “agentic” feature.

- `coz:1474-1608`  
  Defines concrete tool handlers (`list_files`, `read_file`, `grep`, `propose_point`) that the LLM can call. This is where model decisions become file-system actions and structured proposals.

- `coz:640-1137`  
  Implements `coz plot` local server and `/optimize` endpoint that constructs system/user prompts from profiling data + source context, then streams model output to browser clients.

- `viewer/ts/profile.ts:646-761`  
  Frontend streaming client for AI optimization suggestions (`fetch('/optimize')` + NDJSON parsing) with cache and abort controls; operationally couples LLM output to profiler plots.

- `viewer/ts/profile.ts:1401-1542`  
  UI behavior for per-plot “magic wand” optimization panel, including lifecycle management, live progress rendering, and copy/export interactions.

## 6. Use-Case Mapping

The assigned label `Browser / Terminal Use` is **partly accurate but incomplete**.  
Terminal side: `coz suggest-points` is a workflow-automation CLI agent that inspects code and proposes/applies instrumentation (`coz:2372-2416`, `coz:2192-2267`). Browser side: viewer AI optimization runs through local HTTP + web UI (`coz:988-1135`, `viewer/ts/profile.ts:1401-1542`). However, there is no browser automation agent controlling pages/tabs; the browser is a visualization UI.

Best fit after code inspection: **Workflow Automation** (agent assists profiling setup and optimization analysis workflow), not pure Browser/Terminal control.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Custom, provider-agnostic tool-calling agent loop implemented for four backends with similar behavior (`coz:1643-1904`).
  - Clear bounded orchestration (`_SUGGEST_MAX_ITERATIONS`) and explicit tool schema reduce runaway behavior (`coz:1357`, `coz:1381-1442`).
  - Safety checks before file edits (scope filtering, line validation, pre-instrumentation detection, pair validation) (`coz:1905-1963`).
  - Human-in-the-loop diff preview and selective apply flow for proposals (`coz:2102-2170`).
  - Strong integration between causal profile data and prompt context in optimization endpoint (`coz:1020-1081`).

- **Limitations:**
  - Not true multi-agent runtime: one model instance with tool loop, no cooperating roles or inter-agent messaging.
  - Tool API is local and narrow (file list/read/grep/propose only); no richer planning memory/state beyond message history.
  - Regex grep over many files is implemented in Python loops, potentially slow on large repos (`coz:1530-1555`).
  - Security boundaries are lightweight in viewer endpoint (reads arbitrary requested file path for snippets/context) (`coz:704-753`, `coz:1007-1018`).
  - Prompt quality heavily determines outcomes; limited formal evaluation of suggestion accuracy in-code.

- **Research relevance:**
  - Good example of **lightweight agentic workflow automation** without heavyweight frameworks.
  - Demonstrates cross-provider normalization of tool-calling semantics (Anthropic/OpenAI/Bedrock/Ollama) in one codebase.
  - Illustrates practical human-in-the-loop agent output governance via diff preview + selective apply.
  - Useful as evidence of “single-agent tool orchestration” in production-adjacent developer tooling, rather than MAS collaboration.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
