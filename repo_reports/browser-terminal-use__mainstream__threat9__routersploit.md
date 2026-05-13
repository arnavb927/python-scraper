---
repo_name: threat9/routersploit
url: "https://github.com/threat9/routersploit"
stars: 13083
forks: 2392
contributors_count: 89
last_commit_date: "2026-03-02T21:20:04+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:56:04.640060+00:00"
model: auto
duration_s: 157.1
clone_size_kb: 2927
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`threat9/routersploit` is a Python CLI exploitation framework for embedded/network devices (routers, cameras, IoT gear), not an LLM-agent system. A user runs `rsf.py`, enters an interactive terminal, selects modules (`use ...`), configures options (`set ...`), and executes checks/exploits (`run` / `check`) to test vulnerabilities and default credentials (`rsf.py:19-25`, `routersploit/interpreter.py:392-407`). The project dynamically loads hundreds of exploit/scanner/credential modules and provides protocol clients (HTTP, SSH, Telnet, SNMP, etc.) to interact with targets. The practical output is vulnerability verification, credential findings, and exploitation attempts against specified hosts.

## 2. Agent Framework & Architecture

No LLM agent framework is used here. I found no runtime use of LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, OpenAI/Anthropic SDKs, or prompt/planner abstractions in the core code and dependencies (`setup.py:21-27`).

Architecture is a custom modular exploitation engine centered on:
- a command interpreter (`routersploit/interpreter.py`) for orchestration,
- a base exploit abstraction and options metaclass (`routersploit/core/exploit/exploit.py:29-84`),
- dynamic module discovery/import (`routersploit/core/exploit/utils.py:84-139`),
- protocol-specific clients (e.g., HTTP/SSH/Telnet/SNMP) used by exploit modules (`routersploit/core/http/http_client.py:17-59`, `routersploit/core/ssh/ssh_client.py:20-75`).

The “intelligence” is deterministic module logic (checks, protocol interactions, payload construction), not LLM reasoning. Even the “AutoPwn” scanner is a threaded module runner over exploit classes, not an AI planner (`routersploit/modules/scanners/autopwn.py:61-94`).

## 3. Orchestration Pattern

Closest pattern: **other (modular CLI dispatcher + threaded task execution)**, not multi-agent orchestration.

Control flow is command-driven: interpreter parses user input, loads module, and calls `run()`/`check()` on the selected module.

```392:407:routersploit/interpreter.py
@module_required
def command_run(self, *args, **kwargs):
    print_status("Running module {}...".format(self.current_module))
    try:
        signal.signal(signal.SIGINT, self.__command_sigint_handler)
        self.current_module.run()
    ...
def command_exploit(self, *args, **kwargs):
    self.command_run()
```

Dynamic module loading is done through filesystem indexing + import, then instantiation.

```101:116:routersploit/core/exploit/utils.py
def import_exploit(path: str):
    try:
        module = importlib.import_module(path)
        if hasattr(module, "Payload"):
            return getattr(module, "Payload")
        elif hasattr(module, "Encoder"):
            return getattr(module, "Encoder")
        elif hasattr(module, "Exploit"):
            return getattr(module, "Exploit")
```

`autopwn` adds parallelism via worker threads over module iterators (`routersploit/modules/scanners/autopwn.py:80-93`, `routersploit/core/exploit/exploit.py:85-123`), but there are no cooperating LLM agents.

## 4. Tools & External Integrations

- **Terminal/OS command execution**: direct shell execution from interpreter (`routersploit/interpreter.py:617-619`).
- **HTTP(S) integration**: `requests`-based client wrapper (`routersploit/core/http/http_client.py:1-59`).
- **SSH integration**: `paramiko` client for auth, command exec, file transfer, interactive shell (`routersploit/core/ssh/ssh_client.py:2-4`, `20-75`, `141-155`, `227-275`).
- **Telnet integration**: `telnetlib`/`telnetlib3` client (`routersploit/core/telnet/telnet_client.py:1-4`, `16-49`).
- **SNMP integration**: `pysnmp` async API (`routersploit/core/snmp/snmp_client.py:1-3`, `59-77`).
- **Filesystem-backed module/plugin loading**: recursive discovery/import of modules (`routersploit/core/exploit/utils.py:84-99`, `101-139`).
- **Package dependencies confirm above**: `requests`, `paramiko`, `pysnmp`, `pycryptodome` (`setup.py:21-26`).

No MCP servers, browser automation frameworks (Playwright/Browserbase), vector DBs, RAG pipelines, or LLM APIs are wired in this codebase.

## 5. Notable Code Walkthrough

- `rsf.py:19-29` - Main entry point; creates interpreter and chooses interactive vs non-interactive execution.
- `routersploit/interpreter.py:372-407` - Core user-command orchestration (`use`, `run`, `check`) and runtime invocation of selected modules.
- `routersploit/core/exploit/utils.py:84-139` - Dynamic module indexing/import mechanism that enables plugin-style exploit loading.
- `routersploit/core/exploit/exploit.py:29-84` - Base exploit metaclass/abstraction that aggregates user-configurable options and standardizes `run`/`check`.
- `routersploit/modules/scanners/autopwn.py:61-117` - Representative high-level scanner: enumerates many modules, runs vulnerability/default-credential checks concurrently, and aggregates findings.

## 6. Use-Case Mapping

The assigned primary use case **Browser / Terminal Use** is only partially aligned. This project is definitely **terminal-driven** (interactive CLI), but it is not a browser automation or browser-using agent system. Based on actual code, the better category is **Workflow Automation**: it automates security assessment workflows (module selection, protocol probing, vuln/default-cred checks) across many targets/modules from a command-line orchestrator (`routersploit/interpreter.py:620-679`, `routersploit/modules/scanners/autopwn.py:61-117`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Large, consistent plugin architecture with dynamic module discovery/import (`routersploit/core/exploit/utils.py:84-139`).
  - Clear protocol abstraction layers (HTTP/SSH/Telnet/SNMP clients) reusable across modules.
  - Strong operator workflow via interactive CLI and non-interactive mode (`rsf.py:19-25`, `routersploit/interpreter.py:274-315`).
  - Threaded bulk scanning in `autopwn` for practical parallel assessment (`routersploit/core/exploit/exploit.py:85-123`).
  - Extensive exploit/credential module coverage across many vendors/devices (module tree and tests).

- **Limitations:**
  - No LLM, planning, or multi-agent runtime despite “agentic” framing; logic is fully deterministic.
  - No explicit graph/state-machine orchestration primitives; control is mostly imperative CLI dispatch.
  - Heavy reliance on synchronous/imperative networking code; limited centralized retry/backoff policy.
  - Error handling/reporting is often print-based rather than structured telemetry.
  - Some environment scanning triggered AV warnings during repository-wide text search (operational friction for analysis/testing on Windows).

- **Research relevance:**
  - Useful as evidence of **non-LLM modular automation architecture** in offensive-security tooling.
  - Good case study for plugin-based orchestration and protocol-client layering in CLI frameworks.
  - Relevant baseline when contrasting classical automation vs modern LLM multi-agent systems.
  - Not suitable evidence for claims about coordinated LLM-agent behavior.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
