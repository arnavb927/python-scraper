---
repo_name: yologdev/yoyo-evolve
url: "https://github.com/yologdev/yoyo-evolve"
stars: 1687
forks: 110
contributors_count: 3
last_commit_date: "2026-04-23T05:20:26+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, Browser / Terminal Use]
generated_at: "2026-04-27T15:13:40.279152+00:00"
model: auto
duration_s: 84.6
clone_size_kb: 4724
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`yoyo-evolve` is a Rust CLI (`yoyo`) that runs an LLM coding agent against a local repository and, in automation mode, uses that same agent to evolve its own source code continuously. A user can run it interactively (`cargo run` / built binary) as a coding assistant with tools (bash, file edit/read/search, etc.), or run `scripts/evolve.sh` to execute a full autonomous cycle (plan, implement, verify, respond on GitHub). The core value is not just code generation per prompt, but long-horizon workflow automation: issue intake, task planning, implementation, test gates, evaluation loops, and issue responses. In practice, users get an agentic dev workflow that can repeatedly propose and land improvements with guardrails.

## 2. Agent Framework & Architecture

This is **not CrewAI**. It is built on the Rust framework **`yoagent`** (`Cargo.toml:18-20`), with direct imports of `yoagent::agent::Agent`, provider abstractions, tool traits, MCP, OpenAPI, and `SubAgentTool` (`src/main.rs:82-89`, `src/tools.rs:27-36`).

Architecture has two layers:

1. **In-process agent runtime (Rust binary):** `AgentConfig` constructs a single primary agent with model/provider, system prompt, skills, tool set, context compaction limits, and execution limits (`src/main.rs:454-533`, `src/main.rs:568-596`). The main intelligence is in prompts + tool calls + retries (`src/prompt.rs:1263-1478`), with optional delegated subtasks via a dedicated sub-agent tool (`src/tools.rs:1276-1320`).

2. **Outer orchestration harness (shell):** `scripts/evolve.sh` coordinates multiple distinct agent invocations as roles/phases (Assessment, Planning, Task Implementation, Evaluator, Fixer, Issue-Responder), each with tailored prompts and timeouts (`scripts/evolve.sh:619-705`, `scripts/evolve.sh:731-816`, `scripts/evolve.sh:921-997`, `scripts/evolve.sh:1250-1341`, `scripts/evolve.sh:1767-1856`).

So the repo uses both **single-agent with tool use** and **multi-agent role orchestration** at runtime.

## 3. Orchestration Pattern

Closest match: **Hierarchical (manager-worker) workflow automation**, with some sequential pipeline behavior.

- The shell harness acts as manager: it creates role-specific prompts, launches agents, evaluates outputs, and conditionally loops/reverts.
- Worker roles are separated by phase: assessment -> planning -> implementation agents per task -> evaluator agent -> fix agent(s) -> response agent.

Control flow excerpt 1 (manager launching stages):

```388:431:scripts/evolve.sh
run_agent_with_fallback() {
  ...
  "$YOYO_BIN" --model "$MODEL" --skills ./skills ...
}
...
# Phase A1: Assessment
STAGE_NAME=assess run_agent_with_fallback ...
# Phase A2: Planning
STAGE_NAME=plan run_agent_with_fallback ...
```

Control flow excerpt 2 (manager-worker + evaluator/fix loop):

```1250:1326:scripts/evolve.sh
# Phase B-eval: Evaluator agent with fix loop
while [ "$TASK_OK" = true ] && [ "$EVAL_ATTEMPT" -lt "$MAX_EVAL_ATTEMPTS" ]; do
  ... run_agent_with_fallback "$EVAL_TIMEOUT" ...
  if echo "$EVAL_VERDICT" | grep -qi "FAIL"; then
    ... run_agent_with_fallback "$FIX_TIMEOUT" ...
```

There is also nested delegation inside a running agent via `sub_agent` (`src/tools.rs:1302-1320`), reinforcing manager-worker behavior inside turns.

## 4. Tools & External Integrations

- **Local coding tools (through yoagent):** bash, read/write/edit file, list files, search, rename symbol, ask user, todo (`src/tools.rs:1240-1273`).
- **Sub-agent delegation tool:** `SubAgentTool` with inherited provider/model/API key and restricted child tools (`src/tools.rs:1276-1320`).
- **LLM providers:** Anthropic, Google, Bedrock, OpenAI-compatible (`src/main.rs:571-595`; also provider imports in `src/main.rs:85-87`).
- **MCP servers:** dynamic stdio MCP connection via `with_mcp_server_stdio`, with collision preflight (`src/main.rs:132-152`, `src/main.rs:165-287`).
- **OpenAPI tool import:** `with_openapi_file` loads API specs into callable tools (`src/main.rs:289-307`).
- **GitHub integration (automation harness):** heavy `gh` usage for issue list/comment/close/create and CI log inspection (`scripts/evolve.sh:439-447`, `scripts/evolve.sh:457-547`, `scripts/evolve.sh:1448-1466`, `scripts/evolve.sh:1848-1856`).
- **Build/test toolchain integration:** `cargo build/test/clippy/fmt` gates and fix loops in evolution script (`scripts/evolve.sh:980-981`, `scripts/evolve.sh:1368-1387`).
- **No vector DB / RAG store pipeline observed:** memory is file-based JSONL/Markdown context, not embedding retrieval infra (`src/memory.rs` usage and `memory/*` references in script prompts at `scripts/evolve.sh:651-652`).

## 5. Notable Code Walkthrough

- `src/main.rs:454-596`  
  Defines `AgentConfig` and central agent construction. This is where model/provider, tools, skills, context limits, and execution limits are assembled, making it the runtime core.

- `src/tools.rs:1240-1320`  
  Builds primary tool set and the `sub_agent` delegation tool. This file determines what the model can actually do in the environment.

- `src/prompt.rs:775-977`  
  Streaming event loop for prompt execution: consumes `AgentEvent`s, tracks tool calls/results, captures errors, and logs usage. This is the live agent-turn interpreter.

- `src/prompt.rs:1263-1478`  
  Implements retry logic, context-overflow compaction, and auto-retry after tool failures. This is where resilience behavior is encoded.

- `scripts/evolve.sh:619-705`, `scripts/evolve.sh:921-1089`, `scripts/evolve.sh:1250-1427`, `scripts/evolve.sh:1767-1856`  
  The multi-agent orchestration script: phase prompts, per-task loops, evaluator/fixer loop, rollback logic, and GitHub response automation.

## 6. Use-Case Mapping

The assigned primary use case (**Code Generation**) is partly correct but incomplete. The code generation capability is real (implementation agents edit Rust files, run tests, and commit in Phase B), but the repository’s stronger identity is **end-to-end autonomous workflow orchestration** around software maintenance. It coordinates planning, implementation, evaluation, recovery loops, CI awareness, and GitHub communications in one pipeline (`scripts/evolve.sh:619-705`, `scripts/evolve.sh:921-997`, `scripts/evolve.sh:1250-1341`, `scripts/evolve.sh:1767-1856`).

Given that behavior, the better final category is **Workflow Automation** (with code generation as a major sub-capability).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear separation between agent runtime (`src/`) and orchestration harness (`scripts/evolve.sh`), enabling reproducible cycles.
  - Real multi-agent role decomposition (planner/implementer/evaluator/fixer/responder), not just marketing labels.
  - Strong safety/robustness patterns: protected-file checks, retries, checkpoint-restart, and post-change verification gates.
  - Broad integration surface: MCP, OpenAPI, multi-provider backends, shell and GitHub operational tooling.
  - Built-in sub-agent delegation (`sub_agent`) enables hierarchical decomposition within a single conversation.

- **Limitations:**
  - Orchestration is mostly shell-script driven; limited formal typed state machine compared to graph frameworks.
  - Heavy reliance on prompt contracts and file artifacts (`session_plan/*.md`) can be brittle under LLM drift.
  - Quality control evaluator still model-based; correctness remains only partially grounded in tests and heuristics.
  - Uses some destructive git recovery (`git reset --hard`) in automation loops, which is effective but risky if safeguards fail.
  - Provider fallback and retries improve uptime but may still mask root-cause API/tooling instability.

- **Research relevance:**
  - Good real-world example of **hierarchical multi-agent software engineering loops** with explicit role prompts.
  - Demonstrates hybrid architecture: **LLM-agent core + deterministic external orchestrator**.
  - Useful evidence for studies on **self-improving/continuous agent pipelines** with safety gates and rollback behavior.
  - Shows practical integration of agent systems with developer infrastructure (git, CI logs, issues, MCP/OpenAPI).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
