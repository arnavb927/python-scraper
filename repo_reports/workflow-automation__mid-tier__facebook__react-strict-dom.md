---
repo_name: facebook/react-strict-dom
url: "https://github.com/facebook/react-strict-dom"
stars: 3502
forks: 192
contributors_count: 35
last_commit_date: "2026-04-01T19:59:26+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 4
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T14:53:07.705733+00:00"
model: auto
duration_s: 79.5
clone_size_kb: 4024
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`facebook/react-strict-dom` is a JavaScript/Flow monorepo for building cross-platform UI components, not an AI-agent system. Developers install and use `react-strict-dom` in React web/native apps, then write components with `html.*` elements plus `css.create()` so styling and props stay in a strict, shared subset across platforms (`packages/react-strict-dom/src/web/index.js:18-29`). The repo also ships build tooling like a PostCSS plugin that scans source files, transforms style definitions, and emits bundled CSS (`packages/postcss-react-strict-dom/src/builder.js:95-177`). In practice, a user runs standard Node workflows (`npm run build`, app `dev` scripts) and gets compiled library artifacts, generated type definitions, and example apps/docs—not autonomous agent behavior.

## 2. Agent Framework & Architecture

No LLM agent framework is used here (no LangGraph, LangChain, AutoGen, CrewAI, LlamaIndex, or equivalent). Dependency manifests contain frontend/build/test tooling and style compilers, but no model SDKs or agent orchestration libraries (`package.json:19-55`, `packages/react-strict-dom/package.json:39-63`).

Architecture is a component/runtime library plus tooling pipeline:
- UI/runtime layer: strict DOM components and style merging logic (`packages/react-strict-dom/src/web/modules/createStrictDOMComponent.js:30-88`, `packages/react-strict-dom/src/web/runtime.js:21-183`).
- Build/transformation layer: Babel + StyleX extraction and CSS bundling (`packages/postcss-react-strict-dom/src/bundler.js:8-74`).
- Repo automation scripts: release/version/type-generation scripts using filesystem + shell subprocesses (`tools/npm/release.js:11-138`, `packages/scripts/generate-types.js:22-159`).

There is no runtime “intelligence” (prompts, planners, routers, or multi-agent graph state). The only “llms” artifact is documentation text intended to help LLMs understand the library, not to run LLM agents (`packages/website/static/llms.txt:1-450`).

## 3. Orchestration Pattern

Closest match: **other** (deterministic build/runtime pipeline, not MAS orchestration).

Control flow is sequential function orchestration in tooling, e.g., builder configuration -> file discovery -> transform -> bundle:

`packages/postcss-react-strict-dom/src/builder.js:95-106`
```js
function getFiles() {
  const { cwd, include, exclude } = getConfig();
  return globSync(include, { onlyFiles: true, ignore: exclude, cwd });
}

async function build({ shouldSkipTransformError }) {
  const { cwd, babelConfig, useCSSLayers, isDev } = getConfig();
```

`packages/postcss-react-strict-dom/src/builder.js:139-155`
```js
await Promise.all(
  filesToTransform.map((file) => {
    // ...
    return bundler.transform(filePath, contents, babelConfig, { isDev, shouldSkipTransformError });
  })
);

const css = bundler.bundle({ useCSSLayers });
return css;
```

This is process orchestration, but not agent-to-agent coordination.

## 4. Tools & External Integrations

No LLM tools/integrations are wired up. Relevant non-agent integrations are:

- **Babel transform pipeline** via `@babel/core` and StyleX Babel plugin for extracting rules (`packages/postcss-react-strict-dom/src/bundler.js:8-33`, `:61-66`).
- **PostCSS plugin interface** exposed as module entrypoint (`packages/postcss-react-strict-dom/src/index.js:8-10`).
- **Filesystem + glob scanning** for source discovery and incremental rebuilds (`packages/postcss-react-strict-dom/src/builder.js:8-14`, `:95-137`).
- **Node child-process shell automation** for release/publish/git operations (`tools/npm/release.js:12`, `:103-138`).
- **Flow-to-TS type translation toolchain** using `flow-api-translator` (`packages/scripts/generate-types.js:14`, `:66-104`).

No MCP servers, web-search tools, browser automation, vector DBs, or LLM API calls were found in runtime code.

## 5. Notable Code Walkthrough

- `packages/react-strict-dom/src/web/modules/createStrictDOMComponent.js:30-88`  
  Factory for strict HTML-like components; validates allowed props, normalizes a few semantics (`role`, `button` type defaults), merges style layers, and returns typed React components. This is core runtime behavior users consume.

- `packages/react-strict-dom/src/web/runtime.js:21-183`  
  Defines default style resets/mappings for many HTML tags and exports canonical style baselines. It encodes platform-consistent defaults that make “strict DOM” deterministic.

- `packages/postcss-react-strict-dom/src/builder.js:63-177`  
  Stateful build orchestrator: tracks modified files, transforms only changed inputs, and returns bundled CSS output. This is the heart of workflow automation in the build phase.

- `packages/postcss-react-strict-dom/src/bundler.js:11-74`  
  Wrapper around Babel+StyleX metadata extraction; stores per-file style rules and combines them into final CSS. Critical for converting developer-authored styles into runtime assets.

- `tools/npm/release.js:18-138`  
  Monorepo release automation script that updates workspace versions, runs install, optionally commits/tags, and can publish packages. It automates release workflow steps but does not involve AI.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** is partially defensible only in the sense of **build/release automation** (incremental CSS build pipeline and scripted release/publish tasks in `builder.js` and `release.js`). However, after reading source, this repository is fundamentally a **cross-platform UI component library/toolchain**, not an agentic workflow system.

Given your constrained taxonomy, the least-wrong choice remains **Workflow Automation** because there is meaningful automation of developer workflows, but this is **not** LLM-agent automation and not multi-agent runtime behavior.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strongly typed, strict cross-platform component contract with clear runtime validation (`createStrictDOMComponent.js`).
  - Practical build automation with incremental file tracking and selective transforms (`builder.js:112-137`).
  - Mature packaging/release automation for monorepo workspaces (`release.js:44-98`).
  - Clear separation between runtime API, build plugin, and scripts.
  - Includes examples/apps/docs supporting adoption.

- **Limitations:**
  - No LLM, agent, planner, or MAS implementation at runtime.
  - No prompt management, tool-calling loop, or model abstraction layers.
  - “llms.txt” is documentation-facing metadata, not executable agent logic.
  - Some release script choices (e.g., `--no-verify`) may bypass safeguards (`release.js:110`).
  - Researching agent coordination here would be out-of-scope due to domain mismatch.

- **Research relevance:**
  - Useful as evidence of deterministic workflow automation in frontend build systems.
  - Useful for studying monorepo automation scripts and typed cross-platform UI constraints.
  - Not suitable evidence for multi-agent LLM orchestration or collaborative autonomous agents.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
