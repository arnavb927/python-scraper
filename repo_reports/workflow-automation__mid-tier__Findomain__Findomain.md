---
repo_name: Findomain/Findomain
url: "https://github.com/Findomain/Findomain"
stars: 3722
forks: 394
contributors_count: 22
last_commit_date: "2026-02-03T23:23:09+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 4
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T14:50:56.399436+00:00"
model: auto
duration_s: 78.6
clone_size_kb: 4295
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`Findomain` is a Rust CLI tool for automated subdomain discovery and monitoring, not an LLM/agent framework. A user runs commands like `findomain -t example.com` (or batch modes via file/stdin), and the tool queries many passive intelligence sources, validates/normalizes results, and optionally resolves IPs, checks HTTP status, scans ports, takes screenshots, and writes outputs. In monitoring mode, it compares new findings against a PostgreSQL history and pushes alerts to Discord/Slack/Telegram. The core value is fast, parallelized reconnaissance workflow automation for domains, including scheduled/continuous usage patterns. It solves operational enumeration + enrichment + notification pipelines end-to-end.

## 2. Agent Framework & Architecture

No LLM agent framework is used. I found no LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex/OpenAI/Anthropic-style runtime in dependencies or imports (`Cargo.toml:20-42`, `src/*.rs`). The architecture is a custom, concurrent CLI pipeline built with Rust threads, Rayon, Tokio tasks, and channels.

At a high level, `main` parses CLI/config into a large `Args` struct, then dispatches into enumeration or file-driven processing (`src/main.rs:13-76`, `src/args.rs:257-527`). The main orchestrator `get_subdomains()` controls preprocessing (DB/chrome checks, bruteforce/import), discovery (`networking::search_subdomains`), and post-processing (`logic::works_with_data`) (`src/lib.rs:32-112`).

“Intelligence” here is deterministic orchestration/rules, not prompt-based planning: source selection is based on flags/tokens/exclusions, results are merged and filtered, then optionally enriched (DNS/HTTP/ports/screenshots) and sent to storage/webhooks (`src/networking.rs`, `src/logic.rs`, `src/alerts.rs`).

## 3. Orchestration Pattern

Closest match: **event-driven workflow automation with parallel fan-out/fan-in** (not MAS).  
Control is largely sequential at top level, with heavy concurrent workers for source collection and enrichment.

Example fan-out/fan-in in discovery (`src/networking.rs:94-174`):

```94:102:src/networking.rs
let mut all_subdomains: HashSet<String> = vec![
    if args.external_subdomains {
        thread::spawn(move || external_subs::get_amass_subdomains(...))
    } else { thread::spawn(|| None) },
    if args.external_subdomains {
        thread::spawn(move || external_subs::get_subfinder_subdomains(...))
    }  else { thread::spawn(|| None) },
    // ... many source threads ...
]
.into_iter().map(|j| j.join().unwrap())
```

Top-level control routing (`src/lib.rs:72-95`):

```72:75:src/lib.rs
if !args.no_discover {
    let discovered_subdomains = networking::search_subdomains(args);
    args.subdomains.extend(discovered_subdomains);
}
...
logic::works_with_data(args)?;
```

This is a concurrent data pipeline, not planner/worker “agents” exchanging messages.

## 4. Tools & External Integrations

- **Passive subdomain APIs** (CertSpotter, crt.sh API/DB, Sublist3r, Facebook CT, BufferOver, ThreatCrowd, VirusTotal, AnubisDB, Urlscan, SecurityTrails, ThreatMiner, C99), wired in `src/networking.rs:54-172` and implemented in `src/sources.rs:176-503`.
- **External CLI tools**: `amass` and `subfinder` executed via `std::process::Command` in `src/external_subs.rs:11-88`.
- **DNS resolution engine**: `rusolver` async resolver + wildcard detection in `src/networking.rs:243-287` and `src/networking.rs:568-639`.
- **HTTP probing**: `fhc` HTTP client/data collection in `src/networking.rs:305-337`.
- **Port scanning**: async port scanning pipeline in `src/networking.rs:418-475` (calling `port_scanner` module).
- **Browser automation/screenshots**: headless Chrome integration via `headless_chrome` in screenshot flow (`src/networking.rs:370-416`, `Cargo.toml:31`).
- **Database**: PostgreSQL for persistence/query/monitoring state in `src/database.rs:31-180`.
- **Alerting/webhooks**: Discord/Slack/Telegram POST payloads in `src/alerts.rs:17-180`.

No MCP tooling, vector DB, RAG index, browser-agent framework, or LLM API calls are present.

## 5. Notable Code Walkthrough

- `src/main.rs:13-87` - CLI entrypoint and mode dispatcher; routes to reset DB, validate mode, direct target enumeration, or file/stdin pipelines.
- `src/lib.rs:32-112` - Main orchestration function `get_subdomains`; handles prechecks, optional bruteforce/import, discovery call, and final processing.
- `src/networking.rs:50-181` - Core discovery engine; spawns per-source worker threads, joins all results, deduplicates, and validates subdomains.
- `src/networking.rs:213-557` - Enrichment engine for async DNS/IP/HTTP/ports/screenshots and output formatting; major performance and workflow logic.
- `src/alerts.rs:65-140` - Monitoring diff + alert workflow; computes new subdomains vs DB, enriches data, persists and/or pushes webhook notifications.
- `src/sources.rs:176-503` - API adapter layer for many external intelligence providers with typed JSON parsing and error handling.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is correct. The repository automates a recurring security workflow: discover subdomains from many sources, enrich technical metadata (IP/HTTP/ports/screenshots), compare against historical state, then notify channels and persist results for future runs (`src/lib.rs`, `src/networking.rs`, `src/alerts.rs`, `src/database.rs`). It is not an LLM-agent system, but it is clearly an automation pipeline for reconnaissance/monitoring operations.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad multi-source aggregation with concurrent execution and failover behavior (`src/networking.rs`, `src/sources.rs`).
  - End-to-end automation (discovery -> enrichment -> persistence -> alerting) in one CLI (`src/lib.rs`, `src/alerts.rs`).
  - Practical integrations for real ops: PostgreSQL, webhooks, external tools, screenshoting (`src/database.rs`, `src/external_subs.rs`).
  - High-throughput Rust implementation using threads/Rayon/Tokio for performance-critical tasks (`src/networking.rs`).

- **Limitations:**
  - No LLM reasoning, no multi-agent coordination semantics, no planner/router memory abstractions (entire codebase).
  - Some SQL queries are string-formatted directly rather than parameterized (`src/database.rs:108-126`, `149-152`).
  - Error handling often logs-and-continues or exits process, limiting composability as a library (`src/networking.rs`, `src/database.rs`).
  - Monolithic argument/config surface in a single large constructor makes maintainability harder (`src/args.rs:257-527`).

- **Research relevance:**
  - Good evidence for **non-LLM workflow automation** using concurrent fan-out/fan-in pipelines.
  - Useful case study for production-oriented recon orchestration with heterogeneous external services.
  - Relevant to studies comparing “agentic” marketing language vs actual deterministic pipeline implementations.
  - Not suitable evidence for multi-agent LLM collaboration research.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
