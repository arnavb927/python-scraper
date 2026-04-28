---
repo_name: Lissy93/web-check
url: "https://github.com/Lissy93/web-check"
stars: 32863
forks: 2649
contributors_count: 32
last_commit_date: "2026-04-20T22:45:23+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T10:30:37.619544+00:00"
model: auto
duration_s: 78.2
clone_size_kb: 57089
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`Lissy93/web-check` is a full-stack OSINT web inspection tool, not an LLM-agent system. A user runs the app (locally via `yarn dev` / `node server.js`, or deployed), enters a target URL, and receives a dashboard of security/network/content intelligence checks (DNS, TLS, headers, ports, threat feeds, tech stack, etc.). The backend exposes many independent API handlers under `api/*.js`, and the frontend launches those checks and renders card-based results. The output is a consolidated technical profile of a website for security analysis, diagnostics, and reconnaissance.

## 2. Agent Framework & Architecture

No agent framework is used in runtime code (no LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, or LLM SDK wiring). Dependency and import inspection shows standard web stack libraries (`express`, `axios`, `puppeteer`, `wappalyzer`, etc.) but no LLM orchestration components (`package.json:16-59`).

Architecture is a modular “many checks + aggregator UI/API” design:
- Backend: `server.js` dynamically loads every file in `api/` and registers each as an endpoint (`server.js:60-79`), with a common cross-platform wrapper in `api/_common/middleware.js:45-149`.
- Frontend: `src/web-check-live/views/Results.tsx` triggers dozens of fetches through a shared hook (`useMotherHook`) and tracks per-job state (`Results.tsx:251-560` and `hooks/motherOfAllHooks.ts:30-109`).

The “intelligence” here is deterministic programmatic analysis (HTTP calls, DNS lookups, parsing, browser automation), not prompt-driven reasoning or role-based agents.

## 3. Orchestration Pattern

Closest match: **other (fan-out workflow automation / parallel job orchestration)**, not MAS.

Control flow is centrally orchestrated and parallelized in two places:
1) Backend aggregate endpoint runs all handlers concurrently with timeout guards:
`server.js:127-142`
```js
const handlerPromises = Object.entries(handlers).map(async ([route, handler]) => {
  const routeName = route.replace(`${API_DIR}/`, '');
  try {
    const result = await Promise.race([
      executeHandler(handler, req, res),
      timeout(maxExecutionTime, routeName)
    ]);
    results[routeName] = result.body;
```

2) Frontend kicks off many independent jobs via one reusable hook pattern:
`src/web-check-live/views/Results.tsx:308-314`
```ts
const [techStackResults, updateTechStackResults] = useMotherHook({
  jobId: 'tech-stack',
  updateLoadingJobs,
  addressInfo: { address, addressType, expectedAddressTypes: urlTypeOnly },
  fetchRequest: () => fetch(`${api}/tech-stack?url=${address}`).then(res => parseJson(res)),
});
```

So the system is coordinator + task modules, but without LLM “agents” negotiating/planning at runtime.

## 4. Tools & External Integrations

No LLM tools, MCP servers, vector stores, or RAG pipeline are wired in code.

External services/integrations used by the workflow checks include:
- **Headless browser / screenshoting**: Chromium + Puppeteer fallback (`api/screenshot.js:1-142`).
- **Tech fingerprinting**: Wappalyzer (`api/tech-stack.js:1-31`).
- **Threat intelligence APIs**: Google Safe Browsing, URLHaus, PhishTank, Cloudmersive (`api/threats.js:5-97`).
- **Performance audit API**: Google PageSpeed/Lighthouse endpoint (`api/quality.js:13-19`).
- **Network/DNS tooling**: Node DNS resolver calls (`api/dns.js:14-48`), raw WHOIS via TCP/43 + external WHOIS API (`api/whois.js:48-106`).
- **Third-party data from frontend**: ipapi geolocation, Shodan, WhoAPI (`src/web-check-live/views/Results.tsx:277-323`, `:510-513`).

## 5. Notable Code Walkthrough

- `server.js:60-79,97-143` - Core backend orchestrator: auto-discovers API job files, exposes each route, and provides `/api` fan-out endpoint that runs all jobs with per-job timeout handling.
- `api/_common/middleware.js:45-149` - Shared execution wrapper that normalizes URL input, adds platform-specific handler shape (Vercel/Netlify/Node), and enforces timeout/error response behavior.
- `src/web-check-live/views/Results.tsx:251-560` - Main client orchestration surface defining each check (`jobId`, endpoint, transforms) and launching all jobs through a shared hook.
- `src/web-check-live/hooks/motherOfAllHooks.ts:40-109` - Generic async job lifecycle manager (loading/success/error/timeout/retry), reused across every data card.
- `api/threats.js:5-97` - Representative multi-source integration job combining several external threat feeds into one result payload.

## 6. Use-Case Mapping

The assigned primary label (`Simulation`) does **not** fit the code well. This project is best categorized as **Workflow Automation**: it orchestrates a large set of deterministic inspection tasks (network, HTTP, reputation, metadata) over a target URL and aggregates results into a unified report-like UI. There is no simulated multi-agent behavior, no synthetic agent roles, and no LLM-driven environment simulation loop.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear modular job architecture (`api/*.js`) with a common wrapper for consistent behavior.
  - Broad, practical OSINT coverage across DNS, TLS, HTTP, threats, performance, and site metadata.
  - Strong parallelization pattern on both backend (`Promise.all`) and frontend (many concurrent hook jobs).
  - Deployment flexibility across Node/Vercel/Netlify with one middleware abstraction.
  - Good user-facing observability of job states (loading/error/timed-out/retry).

- **Limitations:**
  - Not a multi-agent/LLM system despite “agents” terminology appearing in non-code sponsorship text.
  - Many checks depend on third-party APIs and keys; partial functionality without env configuration.
  - Limited unified planning/prioritization logic; mostly fixed fan-out of predeclared checks.
  - Some external request handling appears brittle/latency-sensitive (timeouts, API dependency failures).
  - Frontend file `Results.tsx` is large and tightly coupled, which may hinder maintainability.

- **Research relevance:**
  - Useful evidence for **non-LLM workflow orchestration** patterns in OSS security tooling.
  - Illustrates modular “task farm” architecture with shared middleware and result aggregation.
  - Relevant as a baseline contrast case in MAS studies: sophisticated orchestration without agent cognition.
  - Demonstrates practical integration of heterogeneous external intelligence APIs in one pipeline.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
