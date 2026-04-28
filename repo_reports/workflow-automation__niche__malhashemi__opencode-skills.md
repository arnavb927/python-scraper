---
repo_name: malhashemi/opencode-skills
url: "https://github.com/malhashemi/opencode-skills"
stars: 481
forks: 27
contributors_count: 6
last_commit_date: "2025-12-23T02:52:40+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T17:15:45.160543+00:00"
model: auto
duration_s: 45.2
clone_size_kb: 123
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`malhashemi/opencode-skills` is a TypeScript plugin for OpenCode that discovers Anthropic-style `SKILL.md` files, validates their frontmatter, and exposes each skill as a dynamic tool at startup. A user installs the plugin in OpenCode, places skills in configured directories, restarts, and then sees tools like `skills_my_skill` available to the assistant. When invoked, a tool injects the skill text into the active session via silent prompts (`noReply: true`) so the model can follow those instructions. In practice, this repo is infrastructure for loading and delivering skill prompts, not a standalone multi-agent runtime.

## 2. Agent Framework & Architecture

The code uses the **OpenCode plugin SDK** (`@opencode-ai/plugin`) plus utility libraries (`gray-matter`, `zod`, Bun `Glob`), not CrewAI/LangGraph/LangChain/AutoGen. The core implementation is in `index.ts`, where `SkillsPlugin` discovers files, parses/validates frontmatter, and returns a map of dynamically generated tools (`index.ts:194-246`).

Architecture is straightforward and centralized:
- **Discovery layer:** scans multiple directories for `SKILL.md` (`index.ts:134-192`).
- **Validation/parsing layer:** parses YAML and enforces schema + naming constraints (`index.ts:44-129`).
- **Runtime tool layer:** registers one tool per discovered skill and injects its content into an OpenCode session (`index.ts:214-246`).

The “intelligence” mostly lives in static skill markdown authored by users; this plugin simply routes that content into the model context. There is no planner, router, or inter-agent coordination implemented here.

## 3. Orchestration Pattern

Closest match: **other (single-stage plugin pipeline)**, not a multi-agent orchestration pattern.

Control flow is linear: discover skills -> create tools -> execute selected tool -> inject two silent prompts. Example flow wiring:

```205:246:index.ts
const skills = await discoverSkills([...])

const tools: Record<string, any> = {}
for (const skill of skills) {
  tools[skill.toolName] = tool({
    description: skill.description,
    args: {},
    async execute(args, toolCtx) { ... }
  })
}
return { tool: tools }
```

Tool execution just pushes context messages, then returns confirmation:

```223:241:index.ts
const sendSilentPrompt = (text: string) =>
  ctx.client.session.prompt({
    path: { id: toolCtx.sessionID },
    body: { agent: toolCtx.agent, noReply: true, parts: [{ type: "text", text }] },
  })

await sendSilentPrompt(`The "${skill.name}" skill is loading\n${skill.name}`)
await sendSilentPrompt(`Base directory for this skill: ${skill.fullPath}\n\n${skill.content}`)
return `Launching skill: ${skill.name}`
```

## 4. Tools & External Integrations

- **OpenCode plugin runtime / session API** (`@opencode-ai/plugin`, `@opencode-ai/sdk`): plugin definition and session prompt insertion via `ctx.client.session.prompt(...)` (`index.ts:22-23`, `index.ts:223-231`).
- **Filesystem scanning via Bun Glob**: recursive discovery of `SKILL.md` with symlink following (`index.ts:25`, `index.ts:141-146`).
- **Markdown/YAML parsing (`gray-matter`)**: parses frontmatter + markdown body (`index.ts:24`, `index.ts:79-81`).
- **Schema validation (`zod`)**: validates required skill metadata and constraints (`index.ts:27`, `index.ts:44-53`, `index.ts:83-94`).
- **OS/env integration**: reads home/config directories and env vars (`XDG_CONFIG_HOME`, `OPENCODE_CONFIG_DIR`) to assemble discovery paths (`index.ts:28`, `index.ts:195-212`).

No web search APIs, browser automation, vector DBs, RAG stack, or database integrations are wired in this repository.

## 5. Notable Code Walkthrough

- `index.ts:44-53,74-129` - Defines frontmatter schema and `parseSkill()`, enforcing naming/description rules and converting each file into structured `Skill` objects. This is the core quality gate preventing malformed skills from becoming tools.
- `index.ts:63-68` - `generateToolName()` maps nested skill paths to stable tool identifiers (e.g., `skills_document_skills_docx`), which is key to deterministic registration and permission targeting.
- `index.ts:134-192` - `discoverSkills()` scans configured roots, handles missing directories gracefully, and detects duplicate generated tool names. This determines what capabilities become available at runtime.
- `index.ts:194-246` - `SkillsPlugin` entrypoint builds the plugin’s dynamic tool table and defines each tool’s execute behavior (silent prompt insertion + minimal return), which is the operational heart of the repo.
- `package.json:47-61` - Declares dependency on OpenCode plugin SDK and supporting parser/validator libs, confirming this is an OpenCode plugin package rather than an end-user app.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** is only partially accurate. The plugin does automate a workflow step (skill discovery, validation, and runtime injection into agent context), but it does **not** implement an autonomous multi-step agent workflow itself. It is better described as **agent tooling infrastructure** for OpenCode.

Given the allowed categories, the best fit is still **Workflow Automation** (plugin-based automation of skill loading and context injection), but this should be interpreted narrowly as configuration/runtime automation rather than multi-agent task execution.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clean, compact implementation with clear separation of discovery/validation/registration (`index.ts`).
  - Strong input validation with explicit errors (zod + directory-name consistency checks).
  - Practical precedence model for project/global/config skill directories (`index.ts:205-212`).
  - Dynamic tool generation enables scalable skill catalogs without hardcoding tools.

- **Limitations:**
  - No runtime multi-agent logic, planning, routing, or collaboration; it is a single plugin layer.
  - No tests of core behavior despite being central plugin logic (`package.json:42` indicates placeholder test script).
  - Eager loading at startup only; no hot reload path in implementation.
  - Duplicate tool names are only warned on, not resolved with explicit conflict policy beyond order effects.

- **Research relevance:**
  - Useful as evidence of **prompt-as-capability packaging** (skills as portable markdown modules).
  - Demonstrates a practical **tool-mediated context injection** pattern (`noReply` silent prompts).
  - Relevant for studies on **agent extensibility infrastructure**, not for multi-agent coordination algorithms.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
