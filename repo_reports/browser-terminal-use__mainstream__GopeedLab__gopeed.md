---
repo_name: GopeedLab/gopeed
url: "https://github.com/GopeedLab/gopeed"
stars: 24075
forks: 1628
contributors_count: 58
last_commit_date: "2026-04-19T11:15:48+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-04-27T10:39:25.631445+00:00"
model: auto
duration_s: 73.3
clone_size_kb: 6939
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`GopeedLab/gopeed` is a cross-platform download manager implemented as a Go backend plus Flutter UI/clients, with support for HTTP, BitTorrent, Magnet, and ed2k workflows. Users run either desktop/mobile/web builds or the CLI (`cmd/gopeed`) to create, monitor, pause/resume, and manage download tasks via the internal downloader engine and REST API (`pkg/rest/server.go:82-149`, `cmd/gopeed/main.go:17-54`). The system persists task state, schedules concurrent downloads, and exposes extension hooks and post-download automation features (`pkg/download/downloader.go:146-299`, `pkg/download/extension.go:254-415`, `pkg/download/script.go:129-161`). It solves high-performance, resumable file-transfer orchestration rather than conversational AI.

## 2. Agent Framework & Architecture

No LLM-agent framework is used. There are no LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex/OpenAI/Anthropic runtime integrations in the Go codebase, and dependency declarations (`go.mod`) likewise show downloader/network/runtime libraries, not LLM SDKs (`go.mod:5-26`).

The architecture is a downloader core with protocol fetchers, task lifecycle management, and extension/script automation. Core control lives in `Downloader` methods for resolve/create/start/watch/error/done transitions (`pkg/download/downloader.go:426-464`, `1294-1384`, `1022-1163`). “Intelligence” here is rule/event-driven extension scripts executed in an embedded JS runtime (goja), where extensions register handlers (`onResolve`, `onStart`, `onError`, `onDone`) and mutate request/task context (`pkg/download/extension.go:37-44`, `338-415`; `pkg/download/engine/engine.go:144-194`). This is programmable automation, not LLM planning/reasoning.

## 3. Orchestration Pattern

Closest match: **event-driven** (with queue-based task scheduling), not multi-agent orchestration.

Control flow is triggered by downloader lifecycle events and callbacks:
- Extension scripts are matched by event + URL/label and invoked synchronously per matching extension (`pkg/download/extension.go:348-405`, `559-588`).
- Task execution uses asynchronous watchers and event emissions (`progress`, `done`, `error`, `finally`) plus queue management for max-running limits (`pkg/download/downloader.go:466-491`, `1022-1089`, `1294-1384`).

Short excerpts:

```338:350:pkg/download/extension.go
func doTrigger[T any](d *Downloader, event ActivationEvent, req *base.Request, ctx T, handler func(ext *Extension, gopeed *Instance, ctx T)) error {
    // ...
    for _, ext := range d.extensions {
        if ext.Disabled { continue }
        for _, script := range ext.Scripts {
            if script.match(event, req) {
```

```1294:1303:pkg/download/downloader.go
func (d *Downloader) doStart(task *Task) (err error) {
    var isCreate bool
    isReturn, err := d.statusMut(task, func() (isReturn bool, err error) {
        if task.Status == base.DownloadStatusRunning || task.Status == base.DownloadStatusDone {
            isReturn = true
            return
        }
        err = d.restoreTask(task)
```

## 4. Tools & External Integrations

There are no LLM tools (no MCP, no vector DB, no web-search LLM toolchain). External integrations are downloader/runtime oriented:

- **HTTP/REST control API** via Gorilla mux/handlers: task CRUD, config, extension install/update, proxy route (`pkg/rest/server.go:122-149`).
- **Browser/WebView automation runtime** exposed to extension JS (`gopeed.runtime.webview` with open/goto/execute/cookies): wired in `pkg/download/extension_runtime_webview.go:72-229`; RPC contract in `pkg/download/engine/webview/rpc.go:5-29`.
- **Embedded JavaScript engine (goja + event loop)** for extension script execution and polyfilled web APIs (`pkg/download/engine/engine.go:144-194`).
- **Git integration** to install/update extensions from repositories (`go-git` clone): `pkg/download/extension.go:190-231`.
- **Protocol integrations** for HTTP/BT/Magnet/ed2k through fetcher managers and protocol filters (`pkg/download/downloader.go:345-354`, `1455-1463`).
- **Storage backends**: BoltDB or in-memory chosen at server build (`pkg/rest/server.go:94-103`).
- **OS script execution hooks** (`.sh/.py/.js/.ps1/.bat`) for download-done/error events (`pkg/download/script.go:67-100`, `129-161`).
- **Webhook triggering** on task outcomes (called from downloader watch/error paths): `pkg/download/downloader.go:1087-1089`, `1161-1162`.

## 5. Notable Code Walkthrough

- `pkg/download/downloader.go:426-464,1022-1163,1294-1384`  
  Implements the core task lifecycle: resolve resources, start/pause/continue tasks, monitor completion/errors, emit events, run post-processing (webhooks/scripts/auto-extract). This is the central orchestrator of all download workflows.

- `pkg/download/extension.go:254-415,559-588`  
  Defines extension activation model and event dispatch (`onResolve/onStart/onError/onDone`), including script matching by URL/labels and per-event JS execution context. This is the main automation/plugin mechanism.

- `pkg/download/engine/engine.go:144-194,32-62`  
  Builds the embedded JS runtime with event loop and polyfills, and executes script/function calls that extensions rely on. It provides deterministic script execution, not AI inference.

- `pkg/download/extension_runtime_webview.go:72-229`  
  Binds webview/browser primitives into JS (`open`, `goto`, `execute`, `waitForSelector`, cookie APIs), enabling browser-like automation inside extensions.

- `pkg/rest/server.go:82-149`  
  Wires the public API surface and initializes the downloader with storage/network settings; this is how UI/CLI/external clients drive the backend.

## 6. Use-Case Mapping

The assigned `Browser / Terminal Use` label is only partially accurate. While terminal/CLI operation exists (`cmd/gopeed/main.go:17-54`) and browser automation primitives exist through webview for extension scripts (`pkg/download/extension_runtime_webview.go:72-229`), the repository’s primary behavior is end-to-end **download workflow orchestration**: task scheduling, protocol handling, extension-triggered request transformations, webhooks, and post-download scripts (`pkg/download/downloader.go:466-491`, `1022-1089`; `pkg/download/script.go:129-161`). A better final category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Robust event-driven task engine with persistence and lifecycle controls (`pkg/download/downloader.go`).
  - Extensible plugin model with sandboxed-ish JS runtime and explicit activation hooks (`pkg/download/extension.go:338-415`).
  - Rich protocol/tooling integrations (HTTP/BT/Magnet/ed2k, webview automation, git-based extension install).
  - Practical automation endpoints: REST API, webhooks, and host script execution.
  - Cross-platform architecture (Go backend + Flutter clients) with CLI and web modes.

- **Limitations:**
  - No LLM model integration, prompt layer, planner/router, or multi-agent runtime; cannot be studied as MAS execution code.
  - Extension execution path appears mostly sequential and event-local, with limited isolation guarantees beyond runtime boundaries.
  - Operational risk from arbitrary extension/script execution and external repo installs if governance is weak.
  - Complexity concentrated in large `downloader.go`, which may hinder modular reasoning/testing in some areas.
  - Browser automation is helper functionality, not a full agentic browsing planner.

- **Research relevance:**
  - Useful evidence for **event-driven automation platforms** with plugin hooks and lifecycle orchestration.
  - Useful for studying **embedded JS scripting inside systems software** (Go + goja runtime embedding).
  - Relevant to **workflow extensibility patterns** (hooks, script runners, webhooks, plugin matching).
  - Not suitable evidence for coordinated LLM multi-agent systems.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
