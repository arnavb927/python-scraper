---
repo_name: vxcontrol/pentagi
url: "https://github.com/vxcontrol/pentagi"
stars: 15375
forks: 2061
contributors_count: 5
last_commit_date: "2026-04-11T23:23:47+00:00"
primary_use_case: Simulation
user_tier: Mid-Tier
total_score: 9
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-05-05T06:31:44.098551+00:00"
model: auto
duration_s: 110.8
clone_size_kb: 101507
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`vxcontrol/pentagi` is a Go-based autonomous penetration-testing platform where a user submits a high-level security objective (“flow”), and the system decomposes it into tasks/subtasks, executes them in isolated Docker containers, and streams progress/results back through APIs/UI. Runtime behavior is not a simple chatbot: it runs a coordinated team of LLM roles (primary orchestrator + specialist agents) that invoke tools (terminal, file, browser, search, memory) until completion barriers are hit. The backend persists message chains, tool calls, logs, and semantic memory in PostgreSQL/pgvector, enabling long-running and resumable workflows. In practice, users run the backend/frontend stack, start a flow, and receive iterative agent actions plus a final report (`backend/pkg/controller/flow.go:110-275`, `backend/pkg/controller/task.go:281-348`, `backend/pkg/providers/provider.go:650-866`).

## 2. Agent Framework & Architecture

This is a **custom multi-agent framework** built in Go, not LangGraph/CrewAI/AutoGen. The code uses `github.com/vxcontrol/langchaingo` for LLM/tool-call primitives (`llms.MessageContent`, `CallWithTools`) while orchestration logic is project-specific (`backend/pkg/providers/performer.go:48-259`, `backend/pkg/tools/executor.go:241-386`).

Architecture is hierarchical: `FlowWorker -> TaskWorker -> SubtaskWorker` controls lifecycle, while `flowProvider` drives LLM agent chains (`backend/pkg/controller/flow.go:756-896`, `backend/pkg/controller/task.go:281-311`, `backend/pkg/controller/subtask.go:274-328`). The primary agent is prepared per subtask with execution context and system prompt, then executed with delegation handlers (`advice`, `coder`, `maintenance`, `memorist`, `pentester`, `search`) and barrier tools (`done`, optionally `ask`) (`backend/pkg/providers/provider.go:580-648`, `650-866`).

“Intelligence” is split across:
- prompt templates (`backend/pkg/templates/prompts/*.tmpl`, wired in `backend/pkg/providers/provider.go:315-475`, `616-633`),
- role-specific executors/toolsets (`backend/pkg/tools/tools.go:495-1534`),
- chain-control policies (retry, reflector correction, repetition detection, mentor/planner supervision) (`backend/pkg/providers/performer.go:107-167`, `302-381`, `459-470`, `547-706`; `backend/pkg/providers/performers.go:811-955`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with tool-driven inner loops**.

Top-level control is manager-worker: flow manages tasks, task manages subtasks, subtask runs primary agent chain, then task refines plan and continues (`backend/pkg/controller/flow.go:814-839`, `backend/pkg/controller/task.go:284-311`, `backend/pkg/controller/subtasks.go:139-165`).

Within each agent execution, control is iterative tool-call loop until a barrier function stops execution:

```650:761:backend/pkg/providers/provider.go
cfg := tools.PrimaryExecutorConfig{
  Adviser: adviser, Coder: coder, Installer: installer,
  Memorist: memorist, Pentester: pentester, Searcher: searcher,
  Barrier: func(ctx context.Context, name string, args json.RawMessage) (string, error) {
    switch name {
    case tools.FinalyToolName: performResult = PerformResultDone or PerformResultError
    case tools.AskUserToolName: performResult = PerformResultWaiting
```

```107:233:backend/pkg/providers/performer.go
for iteration := 0; ; iteration++ {
  result, err = fp.callWithRetries(...)
  ...
  for _, toolCall := range result.funcCalls {
    response, err := fp.execToolCall(...)
    ...
    if executor.IsBarrierFunction(funcName) { wantToStop = true }
  }
  if wantToStop { return nil }
}
```

## 4. Tools & External Integrations

- **LLM providers (multi-vendor):** OpenAI, Anthropic, Gemini, Bedrock, Ollama, Custom, DeepSeek, GLM, Kimi, Qwen via provider controller (`backend/pkg/providers/providers.go:22-35`, `155-377`, `684-726`).
- **Terminal/file execution in Docker:** per-flow primary container (`RunContainer`), terminal/file tools bound into executors (`backend/pkg/tools/tools.go:397-436`, `525-540`, `789-833`, `988-1030`).
- **Web/browser scraping + screenshots:** browser tool calls private/public scraper endpoints and stores screenshots (`backend/pkg/tools/browser.go:54-67`, `145-257`, `295-314`, `422-470`).
- **Search APIs:** Google, DuckDuckGo, Tavily, Traversaal, Perplexity, Searxng, Sploitus wired into search/assistant executors (`backend/pkg/tools/registry.go:203-248`, `backend/pkg/tools/tools.go:1132-1217`, `613-684`).
- **Vector memory (RAG):** pgvector store for search/store of memory/guides/answers/code; automatic memory writes from allowed tools (`backend/pkg/tools/executor.go:537-620`, `backend/pkg/tools/registry.go:34-41`, `139-154`; `backend/pkg/tools/tools.go:355-363`).
- **Graphiti temporal knowledge graph:** optional client, graph search tool, and storage of agent/tool events (`backend/pkg/providers/providers.go:347-355`, `backend/pkg/tools/tools.go:944-953`, `1061-1070`, `1421-1430`; `backend/pkg/providers/performer.go:910-1129`).
- **Observability/telemetry:** Langfuse spans/agents/tools around chain calls and tool execution (`backend/pkg/providers/performer.go:57-58`, `608-617`; `backend/pkg/tools/executor.go:160-239`).
- **Persistence + streaming:** DB-backed message chains/toolcalls/logs and publisher updates for UI subscriptions (`backend/pkg/providers/performer.go:850-908`, `backend/pkg/controller/flow.go:199-216`, `493-495`).

## 5. Notable Code Walkthrough

- `backend/pkg/controller/flow.go:110-275,756-896` - Creates/loads a flow runtime, wires provider + tools + logging workers, runs task processing loop from user input, and manages stop/resume behavior.
- `backend/pkg/controller/task.go:91-111,281-348` - Generates initial subtasks, executes subtasks sequentially, triggers refinement after each completion, and finalizes with reporter output/state propagation.
- `backend/pkg/providers/provider.go:580-866` - Prepares primary-agent chain prompt/context and executes primary-agent runtime with specialist handlers and `done`/`ask` barrier interpretation.
- `backend/pkg/providers/performer.go:48-259,386-545,547-706` - Core agent-chain engine: retrying LLM calls, parsing tool calls, executing tools, reflector-based recovery, summarization, and loop termination conditions.
- `backend/pkg/tools/tools.go:495-770,958-1235` - Defines role-specific executor toolsets (assistant, primary, pentester, searcher, etc.), concretely encoding who can call which tools/agents.

## 6. Use-Case Mapping

The assigned `Simulation` label is partly off. This repo’s runtime behavior is primarily **autonomous workflow execution**: it orchestrates multi-step task decomposition, delegated specialist calls, iterative tool use, and completion reporting in a persistent pipeline (`backend/pkg/controller/task.go:281-348`, `backend/pkg/providers/performer.go:107-233`). It does simulate team roles (researcher/coder/pentester-like personas), but the dominant product behavior is operational orchestration of pentest workflows, not simulation as an end in itself. Best category: **Workflow Automation** (with strong `Browser / Terminal Use` and `RAG + Agents` secondary traits).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent runtime separation with explicit role-specific executors and tool permissions (`backend/pkg/tools/tools.go:495-1534`).
  - Robust control safeguards: retries, repeating-call detection, reflector recovery, barrier-based termination (`backend/pkg/providers/performer.go:302-381`, `459-470`, `547-706`).
  - Strong operational grounding: Docker isolation + terminal/file/browser tooling + memory-backed continuity (`backend/pkg/tools/tools.go:397-450`, `525-552`; `backend/pkg/tools/executor.go:537-620`).
  - Production-oriented observability and persistence (Langfuse + DB message chains/toolcalls/logs) (`backend/pkg/tools/executor.go:160-239`, `291-354`; `backend/pkg/providers/performer.go:850-908`).

- **Limitations:**
  - Orchestration is complex and mostly imperative; no explicit declarative graph/state-machine layer, which may reduce inspectability/formal verification.
  - Heavy prompt-template dependence for behavior control can make reliability sensitive to model drift (`backend/pkg/providers/provider.go:616-633`, template-driven everywhere).
  - Tool surface is broad and security-sensitive (terminal/network actions); safety relies on policy/prompts and container boundaries rather than formal capability proofs.
  - Limited explicit benchmark/eval harness for end-to-end multi-agent quality beyond provider tests (`backend/pkg/providers/providers.go:936-1077`).

- **Research relevance:**
  - Real-world evidence of hierarchical MAS with LLM tool-calling agents in cyber operations.
  - Practical patterns for recovery loops (reflector/mentor) when tool-call structured output fails.
  - Example of coupling agentic workflows with persistent memory (pgvector + temporal graph) and operational telemetry.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
