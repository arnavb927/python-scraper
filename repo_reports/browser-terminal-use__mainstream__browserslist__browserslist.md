---
repo_name: browserslist/browserslist
url: "https://github.com/browserslist/browserslist"
stars: 13521
forks: 763
contributors_count: 197
last_commit_date: "2026-04-14T17:07:45+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T11:00:25.928826+00:00"
model: auto
duration_s: 59.5
clone_size_kb: 587
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`browserslist` is a JavaScript library and CLI for resolving human-readable browser support queries (for example, `last 2 versions`, `> 0.5%`, `maintained node versions`) into concrete browser/Node version lists used by front-end tooling. Users typically run `npx browserslist` or import the package API, and receive a normalized list like `chrome 124`, `firefox 126`, etc. The core value is configuration sharing: one query definition can drive Babel, Autoprefixer, Stylelint, and other tools consistently. Internally, it combines query parsing with `caniuse-lite`, `node-releases`, and related datasets to compute targets. It is a deterministic query engine, not an AI runtime.

## 2. Agent Framework & Architecture

No LLM/agent framework is used. There are no imports or runtime calls for LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, OpenAI, Anthropic, or similar in source files; the only `agents` symbol refers to browser metadata from `caniuse-lite` (`index.js:1-4`, `index.js:1307-1315`).

Architecture is custom, data-driven query evaluation:
- `parse.js` tokenizes/segments query strings into typed nodes (`matchQuery`, `matchBlock`) using regex patterns (`parse.js:21-41`, `parse.js:44-78`).
- `index.js` defines a `QUERIES` registry mapping regex patterns to `select` functions that execute each query type (`index.js:668-1303`).
- Main execution path is `browserslist()` -> `parseQueries()` -> `resolve()` -> dedupe/sort/cache (`index.js:406-456`, `index.js:458-466`, `index.js:327-370`).

Environment/file-system integration is encapsulated in `node.js` (config discovery, stats loading, region/feature data, warning logic), while `browser.js` provides a constrained client-side fallback that disables file/region/feature operations (`node.js:252-503`, `browser.js:5-54`).

## 3. Orchestration Pattern

Closest match: **other (deterministic rule-engine pipeline)**, not multi-agent orchestration.

Control flow is sequential:
1. Parse user query text into structured nodes.
2. For each node, dispatch to the corresponding query handler.
3. Merge/intersect/subtract results based on `or/and/not`, then sort/cache.

Example flow in parser and resolver:

```67:78:parse.js
module.exports = function parse(all, queries) {
  if (!Array.isArray(queries)) queries = [queries]
  return flatten(
    queries.map(function (block) {
      var qs = []
      do {
        block = matchBlock(all, block, qs)
      } while (block)
      return qs
    })
  )
}
```

```327:338:index.js
function resolve(queries, context) {
  return parseQueries(queries).reduce(function (result, node, index) {
    if (node.not && index === 0) {
      throw new BrowserslistError(
        'Write any browsers query ...'
      )
    }
    var type = QUERIES[node.type]
    var array = type.select.call(browserslist, context, node).map(function (j) {
```

## 4. Tools & External Integrations

No AI-agent tools (MCP, browser automation, web-search agents, vector DBs, LLM APIs) are wired in this repo.

External integrations actually present:
- `caniuse-lite` browser/feature/region datasets for usage/support calculations (`index.js:3`, `node.js:1-2`, `node.js:329-366`).
- `node-releases` release metadata for Node query support (`index.js:2`, `index.js:5`, `index.js:1332-1334`).
- `electron-to-chromium` mapping for Electron queries (`index.js:4`, `index.js:697-706`, `index.js:1153-1165`).
- `baseline-browser-mapping` for Baseline-based selection (`index.js:1`, `index.js:817-867`).
- Local filesystem + module resolution for loading config/stats (`node.js:3-4`, `node.js:290-314`, `node.js:411-460`).
- Optional CLI handoff to `update-browserslist-db` when `--update-db` is used (`cli.js:4`, `cli.js:40-49`).

## 5. Notable Code Walkthrough

- `index.js:406-466` - Main API entrypoint; prepares options/context, loads stats, resolves parsed query nodes, deduplicates, sorts, and caches final browser targets.
- `index.js:668-1303` - Query-definition table (`QUERIES`): this is the core rule engine where each supported query grammar is mapped to a selection algorithm.
- `parse.js:21-78` - Lightweight parser that identifies query types and logical composition (`and`/`or`/`not`) before evaluation.
- `node.js:316-460` - Config and stats loading orchestration (env vars, `package.json`, `.browserslistrc`, parent-directory traversal), enabling project-level workflow automation.
- `cli.js:56-155` - CLI interface parsing flags and rendering browser lists/coverage output; this is what users run in terminal workflows.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is partially true (it has a terminal CLI and computes browser targets), but this repository is better classified as **Workflow Automation** for this taxonomy. It automates a repeatable build/config workflow (resolve target runtimes for tooling) rather than controlling browsers or terminals as autonomous agents. There is no browser automation session management, no terminal-driving AI, and no interactive agent loop. The system is a deterministic config-resolution engine embedded in front-end build pipelines.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Rich, extensible query DSL encoded in a centralized registry (`index.js` `QUERIES` table).
  - Strong ecosystem interoperability via shared config conventions (`node.js` config discovery and env selection).
  - Deterministic and cache-aware execution, suitable for CI/build reproducibility (`index.js:403-466`, `node.js:18-22` caches).
  - Broad data integration (global usage, regional usage, feature support, Node/Electron mappings) without external network dependency at runtime.
  - Mature error handling with domain-specific exceptions (`error.js`, checks across `index.js`/`node.js`).

- **Limitations:**
  - No LLM/agent abstraction; cannot serve as evidence of agent coordination behavior.
  - Large monolithic `index.js` query registry increases maintenance complexity and coupling.
  - Parser is regex-based and custom; evolving grammar can be brittle compared with formal parser tooling.
  - Browser build intentionally disables several capabilities (`browser.js`), reducing parity across environments.
  - Some behavior depends on local files/env state, which can surprise users without clear config hygiene.

- **Research relevance:**
  - Good case study for deterministic rule-based orchestration replacing AI planning in production workflows.
  - Useful evidence for DSL-to-action compilation patterns in developer tooling.
  - Illustrates robust config inheritance/discovery strategies in multi-tool ecosystems.
  - Not suitable as a multi-agent systems benchmark (no runtime agent collaboration).

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
