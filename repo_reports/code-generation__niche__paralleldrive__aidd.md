---
repo_name: paralleldrive/aidd
url: "https://github.com/paralleldrive/aidd"
stars: 340
forks: 26
contributors_count: 8
last_commit_date: "2026-04-19T20:52:29+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:26:46.602048+00:00"
model: auto
duration_s: 91.7
clone_size_kb: 1936
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`paralleldrive/aidd` is a Node.js framework/CLI that installs and runs a structured AI-development workflow rather than being a standalone LLM app server. A user typically runs `npx aidd` to scaffold an `ai/` directory of command/skill prompts, then uses those prompts inside an external coding agent (Cursor/Claude/etc.) to drive discovery, planning, implementation, review, and commit loops. The repo also exposes `npx aidd agent` (and `aidd/agent` API) to spawn a configured agent binary (`claude`, `cursor`, or `opencode`) with a prompt. In practice, users get a “prompt operating system” for software delivery automation, plus scaffold tooling that can execute shell steps and prompt steps.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen as a runtime dependency; there are no corresponding imports in the implementation modules. The architecture is primarily **custom prompt-orchestration + process spawning**: skills/commands are authored as markdown/SudoLang-like specs in `ai/skills/*` and `ai/commands/*`, while JavaScript code handles installation, config resolution, and invoking external agent CLIs (`lib/agent-cli/config.js:13-18`, `lib/agent-cli/runner.js:20-29`).

The “intelligence” mostly lives in prompt artifacts, e.g. orchestrator and task skills that describe role routing and delegation patterns (`ai/skills/aidd-agent-orchestrator/SKILL.md:13-46`, `ai/skills/aidd-task-creator/SKILL.md:35-84`). Runtime JS is intentionally thin: it resolves which agent command to run, then executes it with inherited stdio (`lib/agent-cli/command.js:31-37`, `lib/agent-cli/runner.js:23-47`).

There is also a scaffold execution layer that can run manifest steps mixing shell commands and agent prompts, effectively automating setup pipelines (`lib/scaffold-runner.js:158-183`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) prompt orchestration**, implemented as instructions rather than an in-process agent graph runtime.

- The orchestrator skill positions one “orchestrator” agent that routes work to specialized agents:
```13:22:ai/skills/aidd-agent-orchestrator/SKILL.md
You are an agent orchestrator. You are responsible for coordinating the actions of the other agents...
Agents {
  please: ...
  stack: ...
  productmanager: ...
  tdd: ...
  javascript: ...
}
```

- Parallel/dependency-aware delegation is explicitly defined in the `aidd-parallel` skill:
```57:68:ai/skills/aidd-parallel/SKILL.md
delegate(tasks, branch) {
  1. Call generateDelegationPrompts ...
  3. Build a Mermaid change dependency graph ...
  4. Use the dependency graph to determine dispatch order
  ...
  5. Dispatch each prompt via DelegateSubtasks in dependency order
}
```

Control flow in JS code is mostly sequential automation around this prompt system (e.g., resolve config -> spawn agent, or run manifest step-by-step), not peer-to-peer runtime agents (`lib/scaffold-runner.js:167-183`).

## 4. Tools & External Integrations

- **External LLM agent CLIs** (`claude`, `cursor`, `opencode`) are first-class integrations via presets in `lib/agent-cli/config.js:13-18`, executed via `child_process.spawn` in `lib/agent-cli/runner.js:20-29`.
- **Shell/terminal command execution** for scaffold workflows via manifest `run:` steps (`lib/scaffold-runner.js:20-33`, `lib/scaffold-runner.js:172-175`).
- **Prompt-driven agent execution** for scaffold `prompt:` steps, calling `runAgent` (`lib/scaffold-runner.js:175-181`).
- **GitHub API + GitHub CLI token strategy** for scaffold source resolution/download of releases (`lib/scaffold-resolver.js:40-65`, `lib/scaffold-resolver.js:317-327`).
- **Remote scaffold download + `tar` extraction** (`lib/scaffold-resolver.js:107-143`), enabling extension packages.
- **Browser automation/test ecosystem (indirect)**: scaffold example installs Playwright (`ai/scaffolds/scaffold-example/SCAFFOLD-MANIFEST.yml:5`), and user-test prompts specify real-browser execution (`ai/commands/run-test.md:3-10`, `ai/skills/aidd-user-testing/SKILL.md:61-79`).
- **No built-in vector DB/RAG backend/MCP server runtime wiring** found in code; RAG-like behavior is not implemented as a retrieval system in JS.

## 5. Notable Code Walkthrough

- `lib/agent-cli/config.js:13-177` - Core agent config resolver: supports presets, YAML config files, env override (`AIDD_AGENT_CONFIG`), and `aidd-custom/config.yml` fallback. This is the key abstraction that decouples orchestration prompts from specific agent vendors.
- `lib/agent-cli/runner.js:10-69` - Minimal execution engine that spawns `[command, ...args, prompt]` with inherited stdio and structured error handling; this is the runtime bridge to external LLM agents.
- `lib/scaffold-runner.js:66-183` - Parses `SCAFFOLD-MANIFEST.yml` and executes sequential `run` and `prompt` steps; this is where workflow automation is concretely enacted.
- `ai/skills/aidd-agent-orchestrator/SKILL.md:13-46` - Defines manager-style multi-agent coordination policy in prompt form, including guide selection and routing behavior.
- `ai/skills/aidd-parallel/SKILL.md:43-74` - Defines fan-out delegation and dependency-ordered dispatch for sub-agents, making multi-agent concurrency explicit at the prompt layer.

## 6. Use-Case Mapping

The upstream label `Code Generation` is partially true (the system is intended to help agents generate code), but the implementation is broader and better categorized as **Workflow Automation**. The repository’s concrete mechanics focus on automating an end-to-end software process: discovery -> task planning -> execution -> review -> commit, with scaffold pipelines, command templates, and delegating orchestration (`README.md:72-82`, `ai/commands/task.md:1-8`, `ai/commands/execute.md:1-8`). Code generation is one outcome inside that workflow, not the sole runtime capability.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong separation of orchestration policy (skills/commands) from runtime plumbing (`ai/skills/*` vs `lib/agent-cli/*`).
  - Vendor-flexible agent execution via preset and YAML config (`lib/agent-cli/config.js:13-18`, `44-68`).
  - Practical automation bridge combining shell steps and LLM prompt steps in one manifest (`lib/scaffold-runner.js:158-183`).
  - Explicit multi-agent delegation semantics in prompt artifacts (orchestrator + parallel skills).
  - Good defensive engineering around remote scaffold downloads and errors (`lib/scaffold-resolver.js:287-352`).

- **Limitations:**
  - Multi-agent behavior is largely **instructional/prompt-level**, not enforced as an internal graph runtime with typed state transitions.
  - No native LLM API integration in code; depends on external binaries being installed/working.
  - No built-in observability/telemetry for multi-agent execution quality beyond process exit status.
  - Tooling claims (e.g., browser run-test behavior) are largely prompt contracts rather than guaranteed in-repo executors.
  - Limited hard guarantees about sub-agent isolation/conflict handling beyond textual constraints in skill files.

- **Research relevance:**
  - Useful example of **prompt-defined MAS governance** (manager-worker delegation encoded in reusable skill specs).
  - Evidence for a “thin runtime, thick prompt framework” architecture for agentic software workflows.
  - Demonstrates hybrid orchestration where deterministic shell pipelines and LLM delegation coexist.
  - Suitable for studying portability patterns across multiple external agent providers via command abstraction.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
