---
repo_name: K-Dense-AI/karpathy
url: "https://github.com/K-Dense-AI/karpathy"
stars: 1375
forks: 157
contributors_count: 3
last_commit_date: "2025-12-07T21:45:33+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:02:10.259097+00:00"
model: auto
duration_s: 54.6
clone_size_kb: 62
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`K-Dense-AI/karpathy` is a lightweight agent wrapper that exposes an ML-oriented assistant through Google ADK’s web UI and delegates concrete work to Claude Code-style sub-agents. A user runs `python start.py`, which prepares a local `sandbox` (skills, env vars, Python environment, ML packages) and launches `adk web` for interactive use. At runtime, the main ADK agent interprets user intent and can call a delegation tool to spawn an expert worker with a role-specific system prompt. The output is primarily workflow artifacts in `sandbox` (plans, research notes, code, experiment outputs), not a packaged model-serving product.

## 2. Agent Framework & Architecture

The repo uses **Google ADK** (`google.adk.agents.LlmAgent`) plus **LiteLLM** as the model adapter, and a custom delegation bridge into **Claude Agent SDK** (`claude_agent_sdk.query`). This is confirmed in `karpathy/agent.py` and `karpathy/tools.py`, not just in docs.

Architecture is manager-worker style with one explicitly instantiated root agent (`MainAgent`) that has one tool (`delegate_task`). The root agent’s behavior is mostly prompt-driven via `instructions.yaml` (`main_agent` + `common_instructions`), where the “expert team” roles are defined textually (Plan Creator, Data Engineer, Code Writer, etc.). Actual worker execution happens when `delegate_task` invokes Claude Agent SDK with an appended role prompt and sandbox CWD.

So the “intelligence” is split across: (1) ADK root-agent instruction policy, (2) role prompts passed to delegated workers, and (3) tool-capable Claude worker runtime. There is no explicit graph object or typed multi-node planner in code; orchestration is largely instruction/prompt-based.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)**.

The ADK root agent is the manager and only directly exposed runtime agent; workers are spawned through a delegation tool call:

```16:23:karpathy/agent.py
main_agent = LlmAgent(
    name="MainAgent",
    model=LiteLlm(model=MODEL),
    description="The main agent that makes sure the user's machine learning requests are successfully fulfilled",
    instruction=load_instructions("main_agent"),
    tools=[delegate_task],
    output_key="final_output",
)
```

Control flow from manager to worker is through `delegate_task`, which starts a Claude worker session in `sandbox` with role/context appended:

```35:46:karpathy/tools.py
query_gen = query(
    prompt=f"{COMMON_INSTRUCTIONS}\n\nUser Prompt: {prompt}",
    options=ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": append_system_prompt,
        },
        setting_sources=["user", "project"],
        cwd="sandbox",
        permission_mode="bypassPermissions",
    ),
)
```

## 4. Tools & External Integrations

- **Google ADK web runtime** (`adk web`) for agent hosting/UI; startup orchestration in `start.py:23-31`.
- **LiteLLM model backend** for the ADK agent (`LiteLlm(model=MODEL)`), wired in `karpathy/agent.py:13-19`.
- **Claude Agent SDK** for delegated expert execution (`query`, `ClaudeAgentOptions`, tool-use stream handling), wired in `karpathy/tools.py:25-69`.
- **Filesystem sandbox execution** (`cwd="sandbox"` for delegated tasks; artifacts stored there), in `karpathy/tools.py:44` and setup in `karpathy/utils.py:183-201`.
- **Scientific Agent Skills repo integration** via `git clone` + copy into `sandbox/.claude/skills`, in `karpathy/utils.py:18-76`.
- **Python environment/dependency automation with `uv`** for ML packages in sandbox, in `karpathy/utils.py:84-156`.
- **Environment secret propagation** (`karpathy/.env` -> `sandbox/.env`) in `karpathy/utils.py:158-180`.

No browser automation framework (Playwright/Browserbase), vector DB, or MCP server wiring is implemented in this repo’s runtime path.

## 5. Notable Code Walkthrough

- `karpathy/agent.py:1-23` - Defines the single ADK root `LlmAgent`, sets model from env, loads top-level instructions, and exposes only one actionable tool (`delegate_task`), making this file the core orchestration entrypoint.
- `karpathy/tools.py:13-69` - Implements delegated worker execution through Claude Agent SDK; this is where multi-agent behavior actually happens (manager handing subtask + role prompt to a spawned expert).
- `karpathy/instructions.yaml:1-79` - Encodes the operational policy and pseudo-team design (expert roles, execution loop, artifact expectations); most orchestration logic lives here rather than in structured Python controllers.
- `karpathy/utils.py:18-201` - Builds the execution substrate: downloads skills, prepares sandbox environment, installs ML stack, and copies secrets; critical for making delegated workers productive.
- `start.py:11-31` - User-facing launcher that performs sandbox setup then starts ADK web, defining the practical “how users run it” path.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate. The implementation is primarily a **workflow orchestration system for ML tasks**: it sets up an environment, delegates role-based subtasks, and iterates on artifacts in a sandbox. It does use terminal-style execution internally (via Claude worker/tooling), but there is no first-class browser automation stack and no explicit terminal-control API exposed as the main product goal.  
A better primary category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clean manager-worker decomposition with minimal glue code (`agent.py` + `delegate_task`).
  - Practical environment bootstrapping (skills + ML deps + sandbox) enables reproducible task execution.
  - Prompt-defined expert catalog gives flexible role composition without code changes.
  - Uses established agent runtimes (ADK + Claude Agent SDK) instead of bespoke protocol plumbing.

- **Limitations:**
  - Only one explicit root agent object; “multi-agent” team is mostly prompt convention, not strongly typed/runtime-enforced roles.
  - No explicit task graph/state machine, retry policy, or structured planner object for robust orchestration.
  - `permission_mode="bypassPermissions"` raises safety/governance concerns for delegated execution.
  - Limited observability: no built-in persistent run metadata, eval harness, or experiment tracking abstraction in repo code.
  - Hardcoded environment assumptions (e.g., sandbox paths, `uv`, local clone/copy flow) reduce portability.

- **Research relevance:**
  - Useful example of **prompt-mediated hierarchical delegation** (manager agent delegating to role-specialized workers).
  - Illustrates a hybrid architecture combining two agent ecosystems (ADK frontend + Claude worker backend).
  - Demonstrates lightweight MAS prototyping where coordination policy lives in instruction documents rather than formal graphs.
  - Serves as evidence of “agentic workflow engineering” patterns in applied ML automation tooling.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
