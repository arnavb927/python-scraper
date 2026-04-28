---
repo_name: GoogleChrome/lighthouse
url: "https://github.com/GoogleChrome/lighthouse"
stars: 30084
forks: 9708
contributors_count: 381
last_commit_date: "2026-04-22T21:06:26+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T10:33:01.286920+00:00"
model: auto
duration_s: 83.8
clone_size_kb: 284699
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`GoogleChrome/lighthouse` is a web auditing engine that runs a browser session, gathers runtime artifacts (trace, DevTools protocol logs, DOM/network data), executes many audits, and outputs a Lighthouse Result report (HTML/JSON/CSV). In practice, users run the CLI (for example `lighthouse https://example.com`) or invoke the Node API, and Lighthouse launches/connects to Chrome, analyzes the target page, and writes scored diagnostics and recommendations. The codebase is centered on a gather-then-audit pipeline rather than an LLM runtime. Recent additions include an “Agentic Browsing” config that audits whether websites are easier for AI agents to consume (e.g., `llms.txt`, WebMCP metadata), but Lighthouse itself is still an analyzer, not an AI agent.

## 2. Agent Framework & Architecture

No LLM agent framework is used. I found no imports of LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex/OpenAI/Anthropic SDKs, and no prompt/planner/router code paths (`rg` search over repo for these frameworks returned no matches).

Architecture is Lighthouse’s custom pipeline: gathering via browser instrumentation, then deterministic audits over artifacts. The entrypoint in `core/index.js:57-70` runs navigation/snapshot gathering and then calls `Runner.audit(...)`. The orchestration internals are in `core/gather/navigation-runner.js` (connect browser, start instrumentation, navigate, stop instrumentation, collect artifacts) and `core/runner.js` (validate required artifacts, run audits, score categories, generate report).

The “agentic” pieces are audit targets, not internal agents. `core/config/agentic-browsing-config.js:31-41` wires audits like `webmcp-*` and `agentic/llms-txt`, while gatherers such as `core/gather/gatherers/agentic/llms-txt.js:20-24` and `core/gather/gatherers/webmcp-tools.js:66-75` collect evidence from the page/CDP for scoring.

## 3. Orchestration Pattern

Closest match: **sequential pipeline (custom workflow automation), not MAS**.

Control flow is linear and phase-based:

- Gather, then audit:
  - `core/index.js:57-60` calls `navigationGather(...)` then `Runner.audit(...)`.
- Audits run one-by-one:
  - `core/runner.js:332-340` explicitly loops and says “Run each audit sequentially”.

Short excerpts:

- `core/index.js:57-60`  
  `const gatherResult = await navigationGather(page, requestor, options);`  
  `return Runner.audit(gatherResult.artifacts, gatherResult.runnerOptions);`

- `core/runner.js:335-339`  
  `for (const auditDefn of audits) {`  
  `  const auditResult = await Runner._runAudit(...);`  
  `}`

This is not hierarchical manager-worker, graph-state-machine, or swarm coordination among LLM agents.

## 4. Tools & External Integrations

- **Chrome automation via Puppeteer**: browser connection and page lifecycle for data collection in `core/gather/navigation-runner.js:7, 278-286`.
- **Chrome launch/connect via `chrome-launcher`**: CLI-side browser startup in `cli/run.js:12, 85-90, 203-206`.
- **Chrome DevTools Protocol (CDP)**:
  - Standard domains/events for auditing instrumentation in navigation runner and gatherers.
  - **WebMCP domain** use (`WebMCP.enable`, `WebMCP.toolsAdded`) in `core/gather/gatherers/webmcp-tools.js:70-75`.
  - **Audits domain** issue stream (`Audits.issueAdded`) for WebMCP schema checks in `core/gather/gatherers/webmcp-schema.js:50-54`.
- **HTTP fetch of site artifacts**: `llms.txt` retrieval through Lighthouse fetcher in `core/gather/gatherers/agentic/llms-txt.js:21-24`.
- **Error telemetry (optional) via Sentry**: initialized from CLI in `cli/bin.js:116-127`, captured during runner failures in `core/runner.js:240, 426`.

No MCP server orchestration, no vector DB, no RAG pipeline, and no LLM tool-calling runtime inside this repo.

## 5. Notable Code Walkthrough

- `core/index.js:57-84` - Main programmatic API flow (`navigation`, `snapshot`, `startTimespan`) that hands gathered artifacts to the runner; this is the canonical runtime spine.
- `core/gather/navigation-runner.js:204-230` - Instrumentation lifecycle: start instrumentation, navigate, stop instrumentation, then materialize artifacts; defines the practical execution order.
- `core/runner.js:291-344` - Audit orchestration and scoring pipeline; sequentially executes configured audits and assembles final LHR categories.
- `core/config/agentic-browsing-config.js:31-62` - Defines the “Agentic Browsing” preset and wires `webmcp-*` + `llms-txt` checks, showing how AI-agent-readiness is evaluated.
- `core/gather/gatherers/webmcp-tools.js:66-75` - Hooks CDP `WebMCP` events to collect registered tools from a tested page, a key integration for the new agentic-focused audits.

## 6. Use-Case Mapping

The assigned primary label **Simulation** does not fit this repository’s core behavior. Lighthouse is primarily **Workflow Automation**: it automates a deterministic workflow (browser run -> artifact collection -> audit execution -> report generation) rather than simulating autonomous entities or agent interactions. Even the “agentic browsing” additions are compliance/readiness audits for websites, not runtime AI-agent simulation. A better category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Mature, strongly structured gather→audit architecture with explicit artifact contracts (`core/runner.js`, `docs/architecture.md`).
  - Deep browser-level observability via CDP + trace/devtools logs (`core/gather/navigation-runner.js`).
  - Extensible audit/config system enabling new domains like WebMCP and `llms.txt` without changing core execution model (`core/config/agentic-browsing-config.js`).
  - Clear deterministic orchestration and reproducible outputs suitable for automation pipelines.

- **Limitations:**
  - No runtime LLM-agent coordination, planning, role delegation, or prompt-driven decision loops.
  - “Agentic” support is evaluative only (checks page metadata/protocol conformance), not agent execution.
  - Sequential audit execution can limit throughput versus more parallel scheduling approaches (`core/runner.js:332-340`).
  - Not a framework for building autonomous multi-agent applications.

- **Research relevance:**
  - Useful evidence for **non-LLM agent-readiness benchmarking** of web properties (WebMCP/`llms.txt` compliance checks).
  - Good case study in large-scale, deterministic workflow orchestration over browser telemetry.
  - Relevant as infrastructure that agent systems could consume, but not as an example of MAS runtime design itself.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
