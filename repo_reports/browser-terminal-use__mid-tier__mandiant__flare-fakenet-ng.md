---
repo_name: mandiant/flare-fakenet-ng
url: "https://github.com/mandiant/flare-fakenet-ng"
stars: 2118
forks: 379
contributors_count: 19
last_commit_date: "2026-04-02T19:14:50+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 5
architecture_labels: [Custom/Other]
use_case_labels: [Browser / Terminal Use]
generated_at: "2026-04-27T14:12:18.463525+00:00"
model: auto
duration_s: 59.6
clone_size_kb: 1776
uses_mas: no
final_use_case: Simulation
---
## 1. Overview

`flare-fakenet-ng` is a dynamic network analysis tool used by malware analysts to intercept, redirect, and emulate network traffic on a host under test. A user runs the `fakenet` CLI entry point (`fakenet.fakenet:main`), which loads an INI config, starts protocol listeners (HTTP, DNS, FTP, SMTP, etc.), and optionally activates an OS-specific traffic diverter (`setup.py:42-45`, `fakenet/fakenet.py:365-440`). In practice, this makes malware think it is talking to real internet services while FakeNet captures and manipulates those flows locally. The tool then logs activity and can generate a Network-Based Indicators (NBI) HTML report at shutdown (`fakenet/diverters/diverterbase.py:1996-2018`).

## 2. Agent Framework & Architecture

This repository does **not** use an LLM agent framework (no LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex/OpenAI/Anthropic imports found in source). The architecture is a custom, rule-based network interception system built around a central controller (`Fakenet`) plus pluggable listeners and OS-specific diverters (`fakenet/fakenet.py:40-64`, `fakenet/fakenet.py:151-203`, `fakenet/listeners/__init__.py:3-12`).

At startup, `Fakenet.start()` selects a Linux or Windows diverter, instantiates configured listener classes dynamically, starts all listeners, then starts the diverter and wires callback interfaces between them (`fakenet/fakenet.py:214-279`). The “intelligence” is deterministic packet-processing logic in `DiverterBase` and platform subclasses, not prompt/planner logic (`fakenet/diverters/diverterbase.py:1178-1291`, `fakenet/diverters/linux.py:57-93`, `fakenet/diverters/windows.py:184-195`).

So this is custom systems/network software, not an agentic-AI runtime.

## 3. Orchestration Pattern

Closest match: **event-driven** (packet and socket events), with callback pipelines.

Control flow is event/callback based: packet hooks fire, then ordered callback lists process packets.

```184:195:fakenet/diverters/windows.py
cb3 = [
    self.check_log_icmp,
    self.redirIcmpIpUnconditionally
    ]
cb4 = [
    self.maybe_redir_port,
    self.maybe_fixup_sport,
    self.maybe_redir_ip,
    self.maybe_fixup_srcip,
    ]
self.handle_pkt(pkt, cb3, cb4)
```

`handle_pkt` then applies L3 and L4 callback sequences over each packet:

```1247:1281:fakenet/diverters/diverterbase.py
for cb in callbacks3:
    cb(crit, pkt)

if pkt.proto:
    if len(callbacks4):
        if not no_further_processing:
            for cb in callbacks4:
                cb(crit, pkt, pid, comm)
```

This is not manager-worker or graph-of-agents orchestration; it is packet-event processing.

## 4. Tools & External Integrations

No LLM tools/APIs are wired at all. The key external integrations are OS/network and protocol libraries:

- **OS packet interception**
  - Windows via `pydivert` / WinDivert (`fakenet/diverters/windows.py:7`, `fakenet/diverters/windows.py:129-132`)
  - Linux via `netfilterqueue` and iptables orchestration (`fakenet/diverters/linux.py:11`, `fakenet/diverters/linux.py:111-157`)
- **Protocol emulation/listeners**
  - DNS via `dnslib` (`fakenet/listeners/DNSListener.py:8`)
  - FTP via `pyftpdlib` (`fakenet/listeners/FTPListener.py:16-19`)
  - HTTP/SMTP/POP/IRC/TFTP/Proxy via Python socket/socketserver stack (`fakenet/listeners/HTTPListener.py:11-16`, `fakenet/listeners/ProxyListener.py:3-14`)
- **TLS/cert handling**
  - `pyOpenSSL` and `cryptography` for certificate generation/wrapping (`fakenet/listeners/ssl_utils/__init__.py:14-16`)
- **Reporting/output**
  - Jinja2 for rendering NBI HTML reports (`fakenet/diverters/diverterbase.py:2007-2017`)
- **Packet parsing/capture**
  - `dpkt` for packet decode/pcap writing (`fakenet/diverters/diverterbase.py:1068-1070`, `fakenet/diverters/diverterbase.py:1171-1177`)

## 5. Notable Code Walkthrough

- `fakenet/fakenet.py:65-279` - Main orchestrator: parses config, selects diverter by OS, instantiates listener classes dynamically, starts components, and injects cross-component callbacks.
- `fakenet/diverters/diverterbase.py:1178-1291` - Core packet-processing engine: applies network/transport callback chains, writes pcap, and centralizes redirection/rewriting logic.
- `fakenet/diverters/linux.py:94-203` - Linux runtime wiring: installs iptables/NFQUEUE hooks and binds packet handlers for incoming/outgoing/nonlocal flows.
- `fakenet/diverters/windows.py:153-201` - Windows runtime wiring: receives packets from WinDivert, runs callback pipeline, and reinjects modified packets.
- `fakenet/listeners/ProxyListener.py:164-313` - Protocol-agnostic proxy listener that “tastes” traffic, chooses best listener, and bridges sockets while reporting source-port mappings to diverter callbacks.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** looks incorrect for this repository. This code is a malware-analysis network interception/emulation engine, not a browser automation or terminal-use agent.

Better category from the provided list: **Simulation**. It simulates network services and traffic behavior to observe endpoint behavior under controlled conditions (`fakenet/listeners/*`, `fakenet/diverters/*`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Mature cross-platform interception design with separate Linux/Windows diverters and shared logic in `DiverterBase`.
  - Clear event-driven callback architecture for packet mangling and policy decisions.
  - Broad protocol emulation coverage (HTTP/DNS/FTP/SMTP/POP/IRC/TFTP/proxy) with configurable behavior.
  - Practical analyst outputs including pcap capture and structured NBI/HTML report generation.
  - Extensible listener model via config and dynamic module loading.

- **Limitations:**
  - No LLM components, no agent abstraction, no autonomous planning or reasoning loop.
  - Heavy reliance on privileged OS hooks and platform-specific behavior increases operational complexity.
  - Some control flow still uses `sys.exit()` deep in components, reducing embeddability/testability.
  - Security/runtime robustness concerns around dynamic module loading for custom HTTP handlers.
  - MultiHost logic appears less complete than SingleHost in some paths (explicit TODO/pass areas).

- **Research relevance:**
  - Useful as evidence of **event-driven orchestration** in security tooling, not multi-agent AI.
  - Good case study for callback-pipeline architectures in network traffic transformation.
  - Relevant for research on malware analysis infrastructure and protocol/service simulation.
  - Not suitable evidence for coordinated LLM-agent systems.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Simulation
