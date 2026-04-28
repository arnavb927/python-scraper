---
repo_name: ReversecLabs/drozer
url: "https://github.com/ReversecLabs/drozer"
stars: 4504
forks: 833
contributors_count: 48
last_commit_date: "2026-04-08T07:54:54+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T13:25:14.795787+00:00"
model: auto
duration_s: 77.8
clone_size_kb: 125732
uses_mas: no
final_use_case: None
---
## 1. Overview

`drozer` is a Python-based Android security assessment framework, not an LLM system. A user runs CLI commands like `drozer console connect`, then executes built-in modules (`run ...`) against a connected Android device/agent to inspect app components, permissions, IPC surfaces, and exploit paths. The codebase implements a client/server protocol between a desktop console and an Android-resident drozer agent, with optional infrastructure mode via a central drozer server. It also includes packaging utilities to build custom Android drozer-agent APKs. The practical output is an interactive pentesting console, module execution results, and remote shell/file operations on the target device.

## 2. Agent Framework & Architecture

No LLM framework is used. I found no LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex/OpenAI/Anthropic runtime wiring in source imports or dependency manifests; dependencies are networking/runtime libraries like Twisted, protobuf, requests, and prompt_toolkit (`pyproject.toml:8-16`).

Architecture is custom RPC and module execution, where “agent” means an Android app/service endpoint, not an AI role. The CLI entrypoint dispatches subcommands (`src/drozer/main.py:10-41`), `console connect` creates a session via `ServerConnector` and then opens an interactive command loop (`src/drozer/console/console.py:81-104`), and commands are routed to drozer modules (`src/drozer/console/session.py:483-518`). The “intelligence” is human-driven and module-authored logic, not model prompts/planners.

On the server side, a Twisted `ProtocolSwitcher` multiplexes incoming connections into HTTP, shell, byte-stream, or drozer protocol handlers (`src/drozer/server/dz.py:71-91`). The drozer protocol handler forwards/reflexively routes protobuf messages and system requests (`src/drozer/server/protocols/drozerp.py:67-80`), while `SystemRequestHandler` coordinates device binding and session lifecycle (`src/drozer/api/handlers/system_request_handler.py:28-126`).

## 3. Orchestration Pattern

Closest match: **event-driven request/response orchestration** (not MAS). Control flow is driven by incoming protocol messages and callbacks, not planner-worker agents.

Example 1 (protocol routing/event dispatch):

```67:80:src/drozer/server/protocols/drozerp.py
if self.device and self.device.hasCallback(message.id):
    response = self.device.callCallback(message.id, message)
elif message.type == Message.REFLECTION_REQUEST:
    self.request_forwarder.handle(message)
elif message.type == Message.REFLECTION_RESPONSE:
    self.response_forwarder.handle(message)
elif message.type == Message.SYSTEM_REQUEST:
    response = self.request_handler.handle(message)
elif message.type == Message.SYSTEM_RESPONSE:
    response = self.response_handler.handle(message)
```

Example 2 (server-level protocol switching):

```71:90:src/drozer/server/dz.py
if data.startswith(b"DELETE") or data.startswith(b"GET") or data.startswith(b"HEAD") or data.startswith(b"POST"):
    return HTTP(self.factory.credentials, self.__file_provider)
elif data.startswith(b"COLLECT"):
    return ShellCollector()
elif data.startswith(b"S"):
    return ShellServer()
elif self.__file_provider.has_magic_for(data.strip()):
    return ByteStream(self.__file_provider)
else:
    return Drozer()
```

## 4. Tools & External Integrations

- **Android drozer agent over custom protobuf transport**: console starts/stops sessions with remote device agent via `ServerConnector` and `SystemRequestFactory` (`src/drozer/connector/server_connector.py:34-82`).
- **Twisted networking runtime**: server listen/dispatch and protocol handling (`src/drozer/server/dz.py:6-42`).
- **Embedded HTTP file service**: upload/download resources for payload delivery and status (`src/drozer/server/protocols/http.py:37-123`, `src/drozer/server/files.py:20-210`).
- **Remote shell tunnel/collection**: supports shell stream broker between device and collector clients (`src/drozer/server/protocols/shell.py:7-57`).
- **TLS key/cert trust management**: certificate trust-on-first-use/verification paths in console connect flow (`src/drozer/console/console.py:230-294`).
- **Remote module repository over HTTP**: module manager downloads module content with `requests` from configured remotes (`src/drozer/repoman/remotes.py:80-99`).
- **Android agent APK build tooling**: wraps `apktool`, `signapk`, `aapt`, Java tooling for custom agent builds (`src/drozer/agent/builder.py:41-67`).

No LLM APIs, vector DBs, browser automation frameworks, MCP servers, or RAG pipelines are wired.

## 5. Notable Code Walkthrough

- `src/drozer/console/session.py:483-568` - Core interactive runtime; resolves module names, executes `module.run(argv)`, and exposes shell shortcuts (`!`/`shell`) used in day-to-day assessments.
- `src/drozer/server/dz.py:44-134` - Multi-protocol server entrypoint; inspects first bytes and switches connection handling to HTTP/shell/byte-stream/drozer protocol implementations.
- `src/drozer/api/handlers/system_request_handler.py:28-126` - Session/device orchestrator for bind/list/start/stop operations; central to connecting console requests to device callbacks.
- `src/drozer/modules/loader.py:65-106` - Dynamic module discovery/import from built-in and user repository paths, enabling extensible testing modules.
- `src/drozer/connector/server_connector.py:61-82` - Client-side session lifecycle RPC (`startSession`, `stopSession`) used by console connect/disconnect flows.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is partially fitting in the “terminal use” sense (interactive CLI and remote shell), but this repository is fundamentally an Android security testing framework rather than an AI browser/terminal agent system. There is no autonomous LLM controller deciding terminal/browser actions; the human operator drives commands directly. A better category from your list is **Workflow Automation** only in a loose sense (scriptable security workflows via modules), though this repo is best understood as a non-LLM security toolkit.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Mature, modular command architecture with dynamic module loading (`src/drozer/modules/loader.py:16-79`).
  - Robust protocol separation (HTTP/shell/drozer/byte-stream) on one server endpoint (`src/drozer/server/dz.py:71-91`).
  - Practical remote assessment features: session management, shell, file serving, payload plumbing (`src/drozer/console/session.py:546-567`, `src/drozer/server/files.py:20-39`).
  - Security-aware connection flow with TLS trust/fingerprint verification options (`src/drozer/console/console.py:244-289`).

- **Limitations:**
  - No LLM or multi-agent AI runtime despite “agent” terminology; unsuitable as evidence for coordinated LLM-agent systems.
  - Several legacy/rough edges (debug prints, Python2-era idioms in some paths) visible in server/module code (`src/drozer/server/dz.py:75-90`, `src/drozer/agent/manager.py:49-71`).
  - Evented networking and callback-heavy flow can be hard to reason about; limited explicit state-machine abstraction (`src/drozer/device.py:67-145`).
  - Limited built-in formal evaluation/testing hooks for orchestration behavior in examined runtime files.

- **Research relevance:**
  - Good reference for **non-LLM** agent/device orchestration in security tooling via custom protocol handlers.
  - Useful example of event-driven session routing between consoles and remote endpoints in offensive security frameworks.
  - Relevant to studies comparing “agent” terminology in cybersecurity tooling vs. modern LLM-agent architectures.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
