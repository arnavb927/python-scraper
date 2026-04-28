---
repo_name: qualisero/awesome-pi-agent
url: "https://github.com/qualisero/awesome-pi-agent"
stars: 578
forks: 39
contributors_count: 3
last_commit_date: "2026-04-05T09:02:30+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, Browser / Terminal Use]
generated_at: "2026-04-27T16:14:00.497479+00:00"
model: auto
duration_s: 55.1
clone_size_kb: 157
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`qualisero/awesome-pi-agent` is primarily an awesome-list repository (`README.md`) plus a Discord scraping utility in `discord_scraping/` that helps maintain that list. A user runs `discord_scraping/run.sh`, which executes a Node.js Puppeteer scraper against Discord channels/forums, extracts GitHub links, and reports repos not yet present in the root `README.md`. The script persists run state and aggregate discoveries under `discord_scraping/data/` (gitignored), enabling incremental scans over time. In practice, this is a curation workflow automation tool for list maintenance, not an LLM runtime project.

## 2. Agent Framework & Architecture

No LLM agent framework is implemented in code. I found no runtime imports/usages of LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, OpenAI/Anthropic SDKs, or prompt/planner abstractions in executable source; the only executable code is browser scraping/orchestration scripts (`discord_scraping/scraper.js`, `discord_scraping/run.sh`).

The architecture is a single-process automation pipeline: `run.sh` invokes `scraper.js`; `scraper.js` launches Chrome via Puppeteer, traverses configured Discord servers/channels/forums, extracts links, filters results heuristically, and writes JSON artifacts. “Intelligence” is rule-based (regex extraction, keyword filters, retry logic), not model-based reasoning.

## 3. Orchestration Pattern

Closest match: **sequential workflow automation** (single worker script), not multi-agent orchestration.

Control flow is strictly staged in `scrape()` (setup browser → iterate servers → scrape channels/forums → filter/extract repos → save outputs/state):

```811:848:discord_scraping/scraper.js
async function scrape(options = {}) {
  const headless = options.headless ?? false;
  // ...
  browser = await setupBrowser(headless);
  const page = await browser.newPage();
  // ...
  for (const [serverId, serverInfo] of Object.entries(state.servers)) {
    if (!serverInfo.enabled) continue;
    const channels = await getChannels(page, serverId, headless);
    const forumIds = Object.keys(serverInfo.forumChannels || {});
```

`run.sh` then performs post-processing checks against the awesome list in sequence (run scraper, compare found repos to `README.md`, report missing entries):

```96:113:discord_scraping/run.sh
# Check for new repos against awesome list
echo -e "\n${BLUE}Checking against awesome list...${NC}\n"
AGGREGATE_REPOS="$SCRIPT_DIR/data/all-repos.json"
if [ -f "$PROJECT_ROOT/README.md" ] && [ -f "$AGGREGATE_REPOS" ]; then
    NEW_REPOS=$(cat "$AGGREGATE_REPOS" | \
        jq -r 'keys[]' 2>/dev/null | \
        while read repo; do
            [ -z "$repo" ] && continue
```

## 4. Tools & External Integrations

- **Browser automation (Puppeteer + Chrome):** wired in `discord_scraping/scraper.js` via `puppeteer-core` launch and page navigation/scraping (`setupBrowser`, `getChannels`, `scrapeChannel`, `scrapeForumChannel`).
- **Discord web UI scraping:** direct navigation to `https://discord.com/channels/...` and DOM extraction in `discord_scraping/scraper.js`.
- **Shell/system commands:** `execSync` calls (`rm`, `rsync`) for Chrome profile sync in `discord_scraping/scraper.js`.
- **Local filesystem persistence:** JSON state/results written with `fs.promises` in `discord_scraping/scraper.js` (`state.json`, per-run files, aggregate repo files).
- **CLI data tooling (`jq`, `rg`, `grep`):** used in `discord_scraping/run.sh` to compare discovered links with `README.md`.
- **No LLM/API tool calling:** no model API integrations, vector DBs, MCP client/server usage, or RAG pipelines in executable code.

## 5. Notable Code Walkthrough

- `discord_scraping/scraper.js:8-35, 811-1074`  
  Main engine: initializes Puppeteer/Chrome profile settings, executes the end-to-end scrape loop, filters results, extracts GitHub repos, and updates run/aggregate state.

- `discord_scraping/scraper.js:416-503, 673-809`  
  Forum-specific logic: exhaustively scrolls Discord forum threads, collects thread URLs, scrapes each thread with retry handling, and aggregates extracted links.

- `discord_scraping/scraper.js:194-330`  
  Authentication resilience: robust login-state detection and interactive/headless recovery logic to avoid scraping login pages as false content.

- `discord_scraping/run.sh:50-94, 96-167`  
  Orchestration wrapper: handles headless fallback-to-interactive login flow, then compares scraped repos/sub-links against the awesome-list README and prints actionable deltas.

- `discord_scraping/package.json:1-13`  
  Confirms minimal dependency surface (`puppeteer-core`, `chrome-remote-interface`) and absence of LLM/agent SDK dependencies.

## 6. Use-Case Mapping

The assigned primary use case (`Code Generation`) does **not** match the implemented code. This repository’s executable logic automates a maintenance workflow: scrape Discord, discover candidate GitHub resources, and report missing awesome-list entries. There is no code synthesis pipeline, no prompt-to-code flow, and no LLM-driven generation step. A better category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Practical end-to-end automation for Discord-to-awesome-list curation with incremental state (`discord_scraping/scraper.js`).
  - Robust operational handling for login/session issues in both headless and interactive modes.
  - Forum-aware scraping pipeline (including deep thread traversal), not just channel messages.
  - Clear, auditable JSON outputs per run that support manual review before list updates.
  - Lightweight dependency footprint and straightforward shell wrapper for operators.

- **Limitations:**
  - No LLM-agent runtime despite “agent” domain naming; not a MAS implementation.
  - Fragile DOM-selector scraping approach tightly coupled to Discord UI changes.
  - Platform assumptions in script internals (`/tmp`, Chrome profile paths, `rsync`) reduce portability.
  - `run.sh` references `all-messages.json`, while `scraper.js` writes `all-messages-raw.json` (potential mismatch risk in sub-entry checks).
  - No automated tests for scraper correctness, parser robustness, or regression safety.

- **Research relevance:**
  - Useful as evidence of **agent ecosystem tooling/curation workflows**, not as multi-agent coordination research.
  - Illustrates real-world browser automation and incremental data collection patterns in community mining.
  - Demonstrates operational heuristics (login detection, retries, noise filters) for brittle web-scraping pipelines.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
