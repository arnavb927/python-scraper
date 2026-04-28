---
repo_name: minipuft/claude-prompts
url: "https://github.com/minipuft/claude-prompts"
stars: 147
forks: 30
contributors_count: 4
last_commit_date: "2026-04-13T08:40:44+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:54:52.686758+00:00"
model: auto
duration_s: 87.3
clone_size_kb: 47106
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`minipuft/claude-prompts` is a TypeScript MCP server that lets users execute reusable prompt templates with optional chains, gates, frameworks, and script automation through a single `prompt_engine` tool. In practice, a user runs the MCP server (stdio/SSE/streamable HTTP) and then calls MCP tools like `prompt_engine`, `resource_manager`, and `system_control` from an MCP client. The server parses symbolic commands (e.g., chained steps, delegation markers, gate operators), builds an execution plan, and runs it through a staged pipeline with session state and quality checks. It solves the problem of making prompt workflows operational and governable (CRUD, validation, retries, gating, telemetry), rather than just storing static prompts.

## 2. Agent Framework & Architecture

This repo does **not** use LangChain, LangGraph, CrewAI, AutoGen, or LlamaIndex imports in runtime code; it is a **custom MCP-native orchestration framework**. The core runtime is a custom `PromptExecutionPipeline` with many ordered stages, created by `PipelineBuilder` and driven by `PromptExecutor` (`server/src/mcp/tools/prompt-engine/core/prompt-executor.ts:76-709`, `server/src/mcp/tools/prompt-engine/core/pipeline-builder.ts:92-380`, `server/src/engine/execution/pipeline/prompt-execution-pipeline.ts:27-289`).

Architecturally, “intelligence” is split across: (a) symbolic command parsing/planning, (b) chain step rendering with framework/gate injection, (c) optional semantic analysis through external LLM APIs, and (d) gate/judge logic. The MCP surface is consolidated into three tools registered by `McpToolRouter` (`prompt_engine`, `system_control`, `resource_manager`) (`server/src/mcp/tools/index.ts:529-882`).

For multi-agent behavior, the project supports delegated chain steps (`==>`) that generate explicit sub-agent handoff instructions (Task/spawn_agent), so a chain can involve coordinated primary + delegated agents (`server/src/engine/execution/parsers/symbolic-operator-parser.ts:513-577`, `server/src/engine/execution/operators/chain-operator-executor.ts:605-637`, `server/src/engine/execution/delegation/renderer.ts:58-85`).

## 3. Orchestration Pattern

Closest fit: **hierarchical manager-worker**, implemented as a **staged pipeline orchestrator**. The manager is the pipeline (`PromptExecutionPipeline`), and workers are stage modules (parsing, planning, gate enhancement, execution, formatting). Delegated chain steps create worker-agent handoffs for sub-agent execution.

Control flow is explicit in stage registration order:

```259:288:server/src/engine/execution/pipeline/prompt-execution-pipeline.ts
this.stages = [
  this.requestStage,
  this.dependencyStage,
  this.lifecycleStage,
  this.identityResolutionStage,
  this.parsingStage,
  // ...
  this.executionStage,
  this.gateReviewStage,
  this.formattingStage,
  this.postFormattingStage,
];
```

Delegation is encoded in parsing (`==>`) and propagated to step execution/CTA:

```516:518:server/src/engine/execution/parsers/symbolic-operator-parser.ts
* - `==>` produces a delegated step (delegated: true) — executed via Task tool sub-agent
```

```435:444:server/src/engine/execution/operators/chain-operator-executor.ts
const callToAction =
  nextStep?.delegated === true
    ? this.buildDelegationCTA(nextStep, stepPrompts.length, gateGuidanceEnabled, chainContext)
    : !isFinalStep
      ? `Use the resume shortcut below ...`
```

## 4. Tools & External Integrations

- **MCP protocol + MCP clients**: server built on MCP SDK and registers tool endpoints (`server/src/runtime/startup-server.ts:7-77`, `server/src/mcp/tools/index.ts:549-858`).
- **HTTP API layer (Express)**: REST routes for prompt management and resource-manager passthrough (`server/src/mcp/http/api.ts:57-179`, `server/src/mcp/http/api.ts:409-418`).
- **External LLM APIs (OpenAI, Anthropic, custom endpoint)**: semantic analyzer integrations call HTTP endpoints directly (`server/src/modules/semantic/integrations/llm-clients.ts:125-150`, `195-216`, `269-278`).
- **Shell/terminal execution**: shell verification gates execute commands via subprocess utility (`server/src/engine/gates/shell/shell-verify-executor.ts:64-89`).
- **Script tool execution (python/node/shell runtimes)**: prompt-scoped script tools are detected and run as subprocesses (`server/src/modules/automation/detection/tool-detection-service.ts:89-132`, `server/src/modules/automation/execution/script-executor.ts:144-156`).
- **Telemetry (OpenTelemetry)**: pipeline creates root/stage spans and emits metrics (`server/src/engine/execution/pipeline/prompt-execution-pipeline.ts:4-5`, `535-565`).

No browser automation stack (e.g., Playwright/Browserbase) is wired in runtime code.

## 5. Notable Code Walkthrough

- `server/src/mcp/tools/prompt-engine/core/prompt-executor.ts:76-709`  
  Main orchestration entry for `prompt_engine`; constructs dependencies, normalizes requests, and lazily instantiates the execution pipeline.

- `server/src/mcp/tools/prompt-engine/core/pipeline-builder.ts:92-380`  
  Wires ~23 stages and supporting services (parsing, scripts, judge selection, gate enhancement, shell verification, execution, formatting), showing the real runtime control graph.

- `server/src/engine/execution/pipeline/prompt-execution-pipeline.ts:70-235`  
  Executes stages in order, supports early termination, tracks context transitions, and records telemetry/metrics/hook events.

- `server/src/engine/execution/parsers/symbolic-operator-parser.ts:293-301, 513-577, 737-769`  
  Parses symbolic operators (`-->`, `==>`, `::`, `%`, `@`, `#`) and generates execution plans with delegated steps and metadata.

- `server/src/engine/execution/operators/chain-operator-executor.ts:292-457, 605-637`  
  Renders each chain step prompt and emits delegation CTA instructions for sub-agents when next steps are marked delegated.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate. The repo has substantial **terminal/shell automation** via shell verification and script runtimes, but no first-class browser automation integration in core runtime. The dominant behavior is orchestrating prompt workflows, stateful chains, gating, and tool-driven execution across MCP tools, which better matches **Workflow Automation** (`server/src/mcp/tools/index.ts:5-11`, `server/src/mcp/tools/prompt-engine/core/pipeline-builder.ts:166-180`, `297-307`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong custom orchestration with explicit, testable stage pipeline and clear ordering guarantees (`server/src/engine/execution/pipeline/prompt-execution-pipeline.ts:244-289`).
  - Rich symbolic command language supporting chains, delegation, gates, frameworks, styles (`server/src/engine/execution/parsers/symbolic-operator-parser.ts:244-424`).
  - Built-in quality governance (gate enhancement/review, shell verify loops, retry control) (`server/src/mcp/tools/prompt-engine/core/pipeline-builder.ts:258-339`).
  - Practical MCP packaging with consolidated tools and transport support (stdio/SSE/streamable-http) (`server/src/runtime/startup-server.ts:58-77`, `server/src/mcp/tools/index.ts:549-872`).
  - Extensive tests covering integration flows including delegation operator behavior (`server/tests/integration/pipeline/delegation-operator-flow.test.ts:83-123`).

- **Limitations:**
  - Multi-agent execution is partly client-mediated (CTA instructs client to spawn sub-agents) rather than fully server-internal worker spawning (`server/src/engine/execution/delegation/renderer.ts:75-85`).
  - High architectural complexity (many stages/services) increases maintenance and onboarding cost.
  - No native browser automation toolchain despite “browser/terminal” heuristic label.
  - Parallel operator parsing exists, but overall runtime remains mostly sequential stage orchestration.
  - External LLM integration appears focused on classification/analysis rather than fully autonomous planning loops (`server/src/modules/semantic/integrations/llm-clients.ts:25-37`).

- **Research relevance:**
  - Useful evidence of **MCP-native agent orchestration** as an alternative to popular agent frameworks.
  - Demonstrates **hybrid governance patterns**: symbolic planning + quality gates + human/client-in-the-loop delegation.
  - Shows how **agentic workflows can be encoded in command operators** and normalized into executable plans.
  - Good case study for **evaluation/control layers** (gate verdicts, retries, phase guards, telemetry) in production-like agent systems.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
