---
repo_name: xnl-h4ck3r/xnLinkFinder
url: "https://github.com/xnl-h4ck3r/xnLinkFinder"
stars: 1542
forks: 187
contributors_count: 3
last_commit_date: "2026-03-08T20:08:28+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:00:10.133806+00:00"
model: auto
duration_s: 72.5
clone_size_kb: 7276
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`xnLinkFinder` is a single-command Python CLI tool for endpoint discovery and related recon outputs, not an AI agent system. Users run `xnLinkFinder` against a URL, URL list, local directory/file, or exported traffic artifacts (Burp/ZAP/Caido/HAR), and it crawls/parses content to extract links, potential parameters, optional target wordlists, and secrets. The core workflow is deterministic parsing plus HTTP fetching with depth, scope filters, and output files. It also supports optional browser-assisted heap snapshot extraction via Playwright for dynamically generated links. In practice, it solves web recon data collection and normalization for security testing pipelines.

## 2. Agent Framework & Architecture

No LLM framework is present. I found no runtime use of LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, OpenAI/Anthropic SDKs, or prompt/planner abstractions in source imports or call sites (`xnLinkFinder/xnLinkFinder.py:6-39`, plus repo-wide keyword scan).

Architecture is custom procedural Python in one large module. The `main()` function builds CLI args and config, iterates user-agent groups, and dispatches input processing (`xnLinkFinder/xnLinkFinder.py:6863-7427`). Core “intelligence” is handcrafted regex/content parsing and rule-based filtering, mainly inside `processUrl`, `getResponseLinks`, `getResponseParams`, and output processors (`xnLinkFinder/xnLinkFinder.py:1634-2076`, `2383-2934`, `6315-6666`, `3551-3588`).

Concurrency exists, but it is worker-process parallelism for throughput, not multi-agent reasoning: multiprocessing pools call the same worker function `processUrl` and merge shared state (`xnLinkFinder/xnLinkFinder.py:3920-4007`, `5890-5937`).

## 3. Orchestration Pattern

Closest match: **other (procedural pipeline with parallel workers)**, not MAS.  
Control flow is a sequential controller (`main` -> `processInput`/`processEachInput` -> optional `processDepth` -> `processOutput`) with multiprocessing map over URLs.

Example control handoff:
```7300:7308:xnLinkFinder/xnLinkFinder.py
if i == 0:  # Only start once
    start_forward_proxy_thread()

# Process the input given on -i (--input) and get all links
processInput()

# If a Burp file, ZAP file, Caido file or directory is processed then ignore userAgents...
if burpFile or zapFile or caidoFile or dirPassed:
    break
```

Example worker parallelization:
```3954:3971:xnLinkFinder/xnLinkFinder.py
p = mp.Pool(
    args.processes,
    initializer=init_worker,
    initargs=(shared_links, shared_oos, shared_params, shared_failed, shared_visited, shared_stop, None, shared_forward_proxy_queue),
)
active_pool = p
try:
    p.map(processUrl, oldList)
```

## 4. Tools & External Integrations

- `requests` HTTP client for active crawling/fetching, retries, proxy support (`xnLinkFinder/xnLinkFinder.py:8`, `2498-2523`).
- `playwright` (optional) for browser-based heap snapshot link extraction (`xnLinkFinder/xnLinkFinder.py:2284-2333`; dependency in `setup.py:67`).
- Burp/ZAP/Caido/HAR parsers for offline traffic sources (`xnLinkFinder/xnLinkFinder.py:5071-5512`, `5571-5660`).
- `BeautifulSoup` for HTML text extraction and parsing (`xnLinkFinder/xnLinkFinder.py:29`, `1606-1632`, `6375-6382`).
- PDF extraction via external binaries (`pdftotext`, `ocrmypdf`) and Python fallback `pypdf` (`xnLinkFinder/xnLinkFinder.py:1326-1480`; deps in `setup.py:68`).
- Local filesystem I/O for input scanning and outputs (`xnLinkFinder/xnLinkFinder.py:4566-4621`, `3551-3588`).
- Background forward-proxy thread/queue to replay discovered links into tools like Burp/Caido (`xnLinkFinder/xnLinkFinder.py:678-892`, `7299-7301`).

No MCP servers, vector DBs, RAG retrievers, or LLM API integrations are wired anywhere.

## 5. Notable Code Walkthrough

- `xnLinkFinder/xnLinkFinder.py:6863-7427` - Main CLI entrypoint: defines arguments, loads config, iterates user-agent groups, triggers processing pipeline, handles graceful shutdown and stop conditions.
- `xnLinkFinder/xnLinkFinder.py:5571-6077` - Input type router: detects whether input is URL/stdin/file/directory/Burp/ZAP/Caido/HAR and dispatches the appropriate processing path.
- `xnLinkFinder/xnLinkFinder.py:2383-2934` - Primary worker logic for URL requests: headers/user-agent selection, rate limit, proxies, retries, content-size/type guards, parsing, and result collection.
- `xnLinkFinder/xnLinkFinder.py:3920-4012` - Depth expansion orchestration: iterative crawling rounds with multiprocessing pools and shared-state merge.
- `xnLinkFinder/xnLinkFinder.py:3551-3588` - Output aggregation/finalization for links, params, secrets, wordlist, OOS domains, and verbose stats.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate. This is definitely a **terminal-first CLI** tool, and it has a limited browser integration (`--heap` Playwright snapshot) for link discovery (`xnLinkFinder/xnLinkFinder.py:2284-2333`). However, its core identity is automated recon/data-processing workflow orchestration over multiple input formats, batching, filtering, and exporting outputs. A better category is **Workflow Automation**, because most functionality is deterministic extraction + pipeline automation rather than interactive browser-agent behavior.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad ingest coverage (live URLs + Burp/ZAP/Caido/HAR + local files/directories) in one CLI pipeline.
  - Practical scaling features: multiprocessing pools, shared state merge, depth loop, rate limiting, memory/time stop guards.
  - Good operational controls for pentest workflows (scope filters mandatory for URL modes, proxy support, retries, output segmentation).
  - Optional dynamic discovery path through Playwright heap snapshots augments static parsing.
  - Built-in parameter and secret extraction alongside endpoint discovery increases downstream utility.

- **Limitations:**
  - No LLMs or multi-agent runtime; cannot support claims of agentic planning/collaboration.
  - Monolithic single-file architecture (~7k+ lines) increases maintenance and testing complexity.
  - Heavy regex/rule dependence can produce false positives/negatives across varied web content.
  - Minimal modular abstraction for strategy extension (e.g., plug-in parser/tool interfaces).
  - Browser capability is narrow (heap snapshot only), not full autonomous browser interaction.

- **Research relevance:**
  - Useful as evidence of **non-agent automation baselines** in security reconnaissance tooling.
  - Illustrates high-throughput procedural orchestration (pool workers + shared-memory merge) as contrast to MAS patterns.
  - Demonstrates hybrid static/dynamic extraction engineering without LLM reasoning loops.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
