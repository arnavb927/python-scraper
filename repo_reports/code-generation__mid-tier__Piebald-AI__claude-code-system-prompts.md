---
repo_name: Piebald-AI/claude-code-system-prompts
url: "https://github.com/Piebald-AI/claude-code-system-prompts"
stars: 9359
forks: 1671
contributors_count: 4
last_commit_date: "2026-04-21T23:17:11+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T11:50:52.243811+00:00"
model: auto
duration_s: 69.9
clone_size_kb: 1766
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`Piebald-AI/claude-code-system-prompts` is primarily an extracted prompt corpus, not an agent runtime. A maintainer runs a Node script (`tools/updatePrompts.js`) against a `prompts-<version>.json` export to reconstruct prompt strings, write them into `system-prompts/*.md`, and regenerate the prompt index in `README.md` with token counts and categories. The repository’s main output is versioned markdown artifacts for Claude Code’s system prompts, tool descriptions, reminders, and subagent prompts. In practice, users consume this repo as reference data (for inspection/diffing/patching workflows), rather than executing a multi-agent application here.

## 2. Agent Framework & Architecture

No agent framework is implemented in this repository codebase (no LangGraph/LangChain/AutoGen/CrewAI runtime imports or orchestration code were found). The only executable source is `tools/updatePrompts.js`, which performs extraction/update automation over prompt data (`tools/updatePrompts.js:1-568`).

“Agent architecture” appears here as **documented prompt content**, not running logic. For example, `agent-prompt-explore.md` and `agent-prompt-plan-mode-enhanced.md` include metadata like `agentType`, `model`, and `disallowedTools`, and define role behavior in natural language (`system-prompts/agent-prompt-explore.md:12-27`, `system-prompts/agent-prompt-plan-mode-enhanced.md:12-24`). These files describe how Claude Code’s external runtime behaves, but this repo does not instantiate or execute those agents.

The operational intelligence in this repo is therefore split into: (a) prompt reconstruction/packaging logic in `updatePrompts.js`, and (b) static prompt text artifacts under `system-prompts/` that describe external agent behaviors.

## 3. Orchestration Pattern

Closest match for this repository itself: **other (single-script ETL/update workflow)**, not a runtime multi-agent orchestration pattern.

Control flow is sequential pipeline logic in `updateFromJSON`: parse JSON, reconstruct prompt text, diff/write files, count tokens via Anthropic API, then rebuild README sections (`tools/updatePrompts.js:320-418`, `tools/updatePrompts.js:423-556`).

Example excerpt (sequential processing and selective token recount):

```320:379:tools/updatePrompts.js
async function updateFromJSON(jsonPath) {
  const jsonData = JSON.parse(readFileSync(jsonPath));
  // ...
  for (const prompt of jsonData.prompts) {
    const filename = nameToFilename(prompt.name);
    const reconstructedContent = reconstructPrompt(prompt);
    // compare/write, track changed/new prompts
  }
  if (promptsToCount.length > 0) {
    const newCounts = await countTokensBatch(promptsToCount);
  }
}
```

The repo *contains* prompt examples of manager-worker delegation, but these are data artifacts, not executable orchestration in this codebase (`system-prompts/system-prompt-subagent-delegation-examples.md:10-47`).

## 4. Tools & External Integrations

- `Anthropic Messages token-count API` (`https://api.anthropic.com/v1/messages/count_tokens`) for token counting during prompt updates, wired in `countTokens()` (`tools/updatePrompts.js:39-65`).
- `npm registry API` (`https://registry.npmjs.org/@anthropic-ai/claude-code`) to fetch release dates for README metadata (`tools/updatePrompts.js:70-99`).
- `Local filesystem` (`fs` read/write/delete/list) for generating and syncing `system-prompts/*.md` and updating `README.md` (`tools/updatePrompts.js:1-14`, `tools/updatePrompts.js:342-357`, `tools/updatePrompts.js:395-403`, `tools/updatePrompts.js:554-555`).
- No vector DB, browser automation runtime, MCP server client, or agent-execution SDK is implemented in repo code. Those appear only as textual tool descriptions in extracted prompt markdown (e.g., `system-prompts/tool-description-teammatetool.md`, `system-prompts/tool-description-webfetch.md`).

## 5. Notable Code Walkthrough

- `tools/updatePrompts.js:39-132` - Implements external API integrations (`count_tokens`) and batched rate-limited token counting; this is core automation logic for keeping token metadata current.
- `tools/updatePrompts.js:141-228` - Converts prompt names into normalized filenames, reconstructs interpolated prompt strings from pieces/identifiers, and wraps them in metadata comments before writing markdown.
- `tools/updatePrompts.js:320-418` - Main update pipeline: ingest JSON export, detect new/changed/deleted prompts, write files, count tokens only when needed, and orchestrate end-to-end refresh.
- `tools/updatePrompts.js:423-556` - Rebuilds README sections by category/subcategory using prompt metadata, including dynamic version/release-date updates.
- `system-prompts/agent-prompt-explore.md:12-27` and `system-prompts/agent-prompt-plan-mode-enhanced.md:12-24` - Representative extracted artifacts showing how upstream Claude Code defines subagent roles (`Explore`, `Plan`) and restrictions; useful for analysis but not executed here.

## 6. Use-Case Mapping

The assigned primary use case (`Code Generation`) does **not** fit this repository’s own implementation. This project does not generate application code via autonomous agents; it automates extraction, normalization, and publication of prompt artifacts. The better category is **Workflow Automation**: a scripted content-sync pipeline that transforms upstream prompt JSON into structured markdown documentation and index metadata (`tools/updatePrompts.js:320-556`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, reproducible prompt-extraction/update pipeline from upstream exports (`tools/updatePrompts.js:320-418`).
  - Efficient incremental behavior (recounts tokens only for changed/new prompts) reduces API cost/time (`tools/updatePrompts.js:374-392`).
  - Strong taxonomy/organization of prompt corpus into agent/system/tool/reminder/data categories (`tools/updatePrompts.js:256-284`, `tools/updatePrompts.js:438-453`).
  - High transparency for prompt evolution research via versioned markdown artifacts in `system-prompts/`.

- **Limitations:**
  - No runnable multi-agent runtime here; only extracted prompt text and one maintenance script.
  - Dependency on external Anthropic and npm endpoints can fail or rate-limit updates (`tools/updatePrompts.js:58-61`, `tools/updatePrompts.js:73-82`).
  - Limited validation/typing; script is plain JS with minimal schema enforcement for input JSON.
  - README regeneration logic is section-structure sensitive and could be brittle if README format shifts (`tools/updatePrompts.js:431-437`, `tools/updatePrompts.js:490-556`).

- **Research relevance:**
  - Good evidence source for studying **prompt-level multi-agent design patterns** (roles, delegation instructions, tool policies) as artifacts.
  - Useful for longitudinal analysis of how production coding-agent prompts evolve across releases.
  - Not suitable as evidence of runtime coordination algorithms or framework-level MAS implementations.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
