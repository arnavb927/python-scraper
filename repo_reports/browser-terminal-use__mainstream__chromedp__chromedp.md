---
repo_name: chromedp/chromedp
url: "https://github.com/chromedp/chromedp"
stars: 12976
forks: 868
contributors_count: 53
last_commit_date: "2026-03-23T21:39:46+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-05-05T07:55:28.819226+00:00"
model: auto
duration_s: 71.6
clone_size_kb: 1160
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`chromedp/chromedp` is a Go library for automating Chrome/Chromium via the Chrome DevTools Protocol (CDP), not an LLM-agent runtime. A user writes Go code that creates a browser context, composes actions (navigate, click, evaluate JS, screenshot/PDF), and runs them with `chromedp.Run(...)` to drive a real browser tab programmatically (`README.md:3-4`, `example_test.go:47-50`). Internally, the library handles browser process allocation, WebSocket communication, target/tab attachment, and event routing (`allocate.go:127-280`, `browser.go:243-343`). The end result is workflow/browser automation primitives for scraping, testing, and scripted interaction with web pages.

## 2. Agent Framework & Architecture

No LLM agent framework is used here. I found no imports or runtime wiring for LangGraph, LangChain, AutoGen, CrewAI, LlamaIndex, OpenAI/Anthropic SDKs, prompt templates, or planner/router modules; this is pure Go CDP automation (`go.mod:5-11`, `chromedp.go:14-31`).

Architecture is a custom browser-automation runtime centered on three abstractions: `Allocator` (starts/connects browser), `Browser` (owns CDP connection and session routing), and `Target` (tab/session executor) (`allocate.go:18-33`, `browser.go:35-90`, `target.go:19-43`). `NewContext` builds a context carrying allocator/browser/target state; `Run` lazily allocates browser and target, then executes a `Tasks` list (`chromedp.go:108-122`, `chromedp.go:325-336`, `chromedp.go:731-743`).

The “intelligence” is not model-driven; it is deterministic orchestration via ordered actions plus event listeners (`ListenTarget`, `ListenBrowser`, `WaitNewTarget`) and CDP event/state handling in goroutines (`chromedp.go:791-870`, `target.go:90-159`, `browser.go:252-343`).

## 3. Orchestration Pattern

Closest match: **event-driven + sequential command pipeline** (i.e., “other” hybrid, not MAS orchestration).

- **Sequential pipeline:** actions are executed strictly in order by `Tasks.Do`:
  - `chromedp.go:736-741` loops over actions and returns on first error.
- **Event-driven runtime:** browser and tab handlers multiplex asynchronous CDP messages and dispatch them to listeners/state updaters:
  - `browser.go:269-299` classifies inbound WebSocket messages (session events, global events, command responses).
  - `target.go:132-156` routes Runtime/Page/DOM events through a synchronous queue to update local frame/DOM/execution-context state.

Control flow is therefore: user action list -> command queue -> CDP responses/events -> listener/state updates -> next action, rather than planner/worker agent handoffs.

## 4. Tools & External Integrations

No LLM “tool calling” stack exists. External integrations are browser/protocol and OS-level:

- **Chrome DevTools Protocol (CDP):** core command/event API via `github.com/chromedp/cdproto` (`chromedp.go:21-30`, `go.mod:6`).
- **WebSocket transport to browser:** `gobwas/ws` used to dial/read/write CDP messages (`conn.go:42-65`, `conn.go:72-142`).
- **Local browser process control:** `exec.CommandContext` starts Chrome with flags/user-data-dir and discovers DevTools WS URL from stdout (`allocate.go:173`, `allocate.go:236-251`, `allocate.go:285-321`).
- **Remote browser attachment:** `NewRemoteAllocator` supports connecting to an existing Chrome endpoint (`allocate.go:517-545`, `allocate.go:560-602`).
- **Filesystem:** temp profile directories and output artifacts (screenshots/PDF in examples) (`allocate.go:151-157`, `example_test.go:404-405`, `example_test.go:430-431`).
- **HTTP endpoints for local tests/examples:** `httptest` servers used in usage examples (`example_test.go:36`, `example_test.go:65`, `example_test.go:286`).

No MCP servers, vector DBs, RAG pipeline, shell-agent loop, or external LLM APIs are wired.

## 5. Notable Code Walkthrough

- `chromedp.go:122-221` — `NewContext` builds execution context state, inheritance, and cleanup semantics; this is the entry point for user-level task execution.
- `chromedp.go:325-336` — `Run` lazily initializes browser/target and executes actions, making it the central orchestration API for all workflows.
- `allocate.go:127-280` — `ExecAllocator.Allocate` launches Chrome, manages profile dirs/lifecycle, extracts DevTools WS URL, then creates `Browser`.
- `browser.go:243-343` — `Browser.run` is the core event loop that reads CDP messages and routes them to the right tab/session queues.
- `target.go:90-159` — `Target.run` processes per-tab event streams, invoking listeners and maintaining runtime/page/DOM state for higher-level actions.

## 6. Use-Case Mapping

This repo strongly realizes **Browser / Terminal Use** through browser automation APIs: navigating pages, interacting with DOM, evaluating JS, managing tabs, and collecting outputs like screenshots/PDF (`example_test.go:47-50`, `example_test.go:298-305`, `example_test.go:394-400`, `example_test.go:416-424`). It also includes terminal-adjacent execution concerns (spawning Chrome process, CLI flags, environment setup) in `ExecAllocator` (`allocate.go:134-173`, `allocate.go:396-515`).  

For MAS classification specifically, the assignment looks wrong: this codebase does **not** implement coordinated LLM agents at runtime. A better category based on code is **Browser / Terminal Use** (or broad workflow automation without agents).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clean layered architecture (`Allocator`/`Browser`/`Target`) separates process, transport, and tab logic (`allocate.go:18-33`, `browser.go:35-90`, `target.go:19-43`).
  - Efficient async CDP handling with explicit queues and goroutines for high-throughput event routing (`browser.go:248-343`, `target.go:95-159`).
  - Practical defaults for headless automation and cross-platform Chrome discovery (`allocate.go:56-84`, `allocate.go:348-394`).
  - Ergonomic high-level API (`Run`, `Tasks`, action combinators) over low-level protocol calls (`chromedp.go:325-336`, `chromedp.go:731-743`).
  - Strong real-world examples covering navigation, waits, tabs, dialogs, screenshots, and PDF (`example_test.go`).

- **Limitations:**
  - No LLM/agent abstractions, planning, memory, or multi-agent coordination primitives (no relevant imports/modules in `go.mod:5-18`).
  - Event/listener callbacks are synchronous and can deadlock if misused; docs warn to avoid blocking (`chromedp.go:796-799`, `chromedp.go:819-822`).
  - Some TODOs indicate known edge cases and potential races/robustness concerns (`chromedp.go:710-713`, `target.go:96-99`).
  - API is Go/CDP-specific; not a general cross-browser agent framework.
  - No built-in persistent task orchestration layer beyond process lifetime/context cancellation.

- **Research relevance:**
  - Useful as evidence for **event-driven browser automation runtime design** rather than MAS.
  - Demonstrates robust engineering patterns for asynchronous protocol clients (message queues, listener lifecycle, context cancellation).
  - Serves as a baseline environment/tool substrate that LLM agents could call externally, but it is not itself an agent system.
  - Relevant to studies comparing deterministic automation frameworks vs. agentic/planner-based systems.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
