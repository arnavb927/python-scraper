---
repo_name: masaic-ai-platform/AgC
url: "https://github.com/masaic-ai-platform/AgC"
stars: 111
forks: 9
contributors_count: 4
last_commit_date: "2026-02-19T07:21:33+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T18:01:39.639440+00:00"
model: auto
duration_s: 97.7
clone_size_kb: 40741
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`AgC` is an open-core server platform that exposes OpenAI-compatible APIs (`/v1/responses`, `/v1/chat/completions`) and adds built-in tool orchestration, MCP connectivity, and vector-search-backed retrieval. In practice, a user runs the Spring Boot service and then points OpenAI SDK clients at it (e.g., `base_url=http://localhost:6644/v1`) so model calls can invoke native tools, MCP tools, and iterative “agentic_search” workflows (`platform/examples/sdk-examples/openai-py-sdk/agcloopwithMCP.py:11-24`, `:84-90`). The platform handles tool-call loops server-side (including streaming), optionally stores conversation/tool traces, and can perform retrieval across vector stores. The output is an OpenAI-like response stream/completion enhanced with tool execution and retrieval reasoning.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/CrewAI/AutoGen/LlamaIndex as the primary runtime framework. It is a **custom orchestration layer** built in Kotlin around OpenAI’s Java SDK, with selective use of LangChain4j for MCP and vector integrations (`platform/open-responses-core/build.gradle.kts:42-50`, `:46-49`; `platform/open-responses-core/src/main/kotlin/ai/masaic/openresponses/tool/ToolService.kt:10-15`).

Architecturally, the “intelligence” is split across:
1. The base LLM (tool-calling model via OpenAI-compatible chat completion).
2. A custom tool runtime (`ToolService` + `NativeToolRegistry` + `MCPToolExecutor`) that resolves aliases, executes tools by protocol, and emits progress events (`ToolService.kt:341-371`; `NativeToolRegistry.kt:74-101`).
3. A specialized iterative retrieval controller called `agentic_search`, where an LLM repeatedly decides `TERMINATE` vs `NEXT_QUERY` using prompt-engineered memory and filtering rules (`AgenticSearchService.kt:188-436`; `PromptBuilder.kt:94-140`, `:189-217`).

So this is best described as a **single-agent tool-calling platform with an internal iterative retrieval agent**, not a multi-agent role graph.

## 3. Orchestration Pattern

Closest match: **sequential iterative loop (recursive tool-calling)** with an internal **plan-refine loop** for retrieval.

Control flow is: model call -> detect tool calls -> execute tool(s) -> append outputs -> recurse into next model call until completion or terminal tool (`image_generation`). This is explicit recursion:

- `MasaicOpenAiResponseServiceImpl.create(...)` recursively calls itself after tool execution (`MasaicOpenAiResponseServiceImpl.kt:87-122`).
- `MasaicOpenAiCompletionServiceImpl.handleToolCalls(...)` similarly recurses with updated messages (`MasaicOpenAiCompletionServiceImpl.kt:100-143`).

Short excerpt:

`platform/open-responses-core/src/main/kotlin/ai/masaic/openresponses/api/client/MasaicOpenAiResponseServiceImpl.kt:115-122`
```kotlin
if (exceedsMaxToolCalls(responseInputItems)) { ... }
return create(client, updatedParams, metadata, parentSpan)
```

Inside `agentic_search`, control is another sequential loop:
- seed search results
- ask LLM for `NEXT_QUERY` or `TERMINATE`
- apply new filters/query
- repeat until max iterations or termination (`AgenticSearchService.kt:188-445`).

`platform/open-responses-core/src/main/kotlin/ai/masaic/openresponses/tool/agentic/AgenticSearchService.kt:342-349`
```kotlin
while (!decisionParsed && retryCount < 3) {
    llmDecision = callLlmForDecision(...)
    ...
}
```

## 4. Tools & External Integrations

- **OpenAI-compatible model calls**: Core generation via `openai-java` client (`MasaicOpenAiResponseServiceImpl.kt:58-61`; `AgenticSearchService.kt:609-617`).
- **Native tools**: `think`, `file_search`, `agentic_search`, `image_generation` registered and executed in `NativeToolRegistry` (`NativeToolRegistry.kt:39-43`, `:91-99`, `:215-313`, `:423-553`).
- **MCP servers (remote tools)**: runtime discovery/execution of MCP tools via `MCPToolExecutor` and `MCPToolRegistry` (`MCPToolRegistry.kt:49-57`, `:67-90`, `:121-127`; `ToolService.kt:225-265`).
- **Vector stores / retrieval backends**: pluggable `VectorSearchProvider` interface with file-based local store and Qdrant implementation (`VectorSearchProvider.kt:14-35`; `FileBasedVectorSearchProvider.kt:33-45`; `QdrantVectorSearchProvider.kt:30-41`).
- **Hybrid retrieval/reranking path**: vector + text indexing helper integration (`QdrantVectorSearchProvider.kt:234-239`; `FileBasedVectorSearchProvider.kt:223-239`; wiring in `VectorSearchConfiguration.kt:37-44`).
- **MongoDB (optional persistence)**: response/completion/vector/eval repositories when configured (e.g., `MongoVectorStoreRepository.kt`, `MongoResponseStore.kt`), with default in-memory/file mode in properties (`application.properties:20-31`).

## 5. Notable Code Walkthrough

- `platform/open-responses-core/src/main/kotlin/ai/masaic/openresponses/api/client/MasaicOpenAiResponseServiceImpl.kt:48-124`  
  Main non-streaming Responses API execution loop; converts requests to completion calls, checks tool calls, executes tools, and recurses until a final response.

- `platform/open-responses-core/src/main/kotlin/ai/masaic/openresponses/api/client/MasaicToolHandler.kt:128-308` and `:646-995`  
  Central tool-call dispatcher for completion/response/streaming modes; distinguishes native vs non-native tools, handles terminal tools, and appends tool outputs into model context.

- `platform/open-responses-core/src/main/kotlin/ai/masaic/openresponses/tool/NativeToolRegistry.kt:24-101` and `:215-313`  
  Defines built-in tools and their execution, including `agentic_search` entrypoint and SSE event emission.

- `platform/open-responses-core/src/main/kotlin/ai/masaic/openresponses/tool/agentic/AgenticSearchService.kt:38-495`  
  Iterative retrieval “agent”: seeds search, prompts LLM for next action, updates query/filters, tracks memory, and terminates based on LLM signal, repetition guard, or iteration cap.

- `platform/open-responses-core/src/main/kotlin/ai/masaic/openresponses/tool/agentic/llm/PromptBuilder.kt:10-222`  
  Where most retrieval-agent behavior is encoded via prompt policy: strict output formats, novelty constraints, chunk filter rules, and memory accumulation format.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** is appropriate. This repo automates end-to-end LLM workflows: request intake, iterative tool-call execution, external MCP invocation, retrieval refinement, and response assembly without client-side orchestration logic (`ResponseController.kt:27-50`; `MasaicOpenAiCompletionServiceImpl.kt:100-143`; `ToolService.kt:341-371`). It is not primarily a code generator or browser agent; it is a server-side orchestration substrate for tool-augmented AI workflows and agentic retrieval.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Production-style recursive tool-call loop for both streaming and non-streaming APIs.
  - Strong MCP integration with dynamic server/tool discovery and caching/invalidation.
  - Clear modular boundaries (controller -> facade/service -> tool handler -> tool registry/executor).
  - Agentic retrieval loop has explicit safeguards (retry parse, repeat detection, max iterations).
  - Supports multiple storage/search backends (file/Qdrant/Mongo patterns).

- **Limitations:**
  - No true multi-agent runtime (no manager-worker teams, no agent graph with distinct LLM roles).
  - `agentic_search` relies heavily on brittle string-format prompting/parsing (`NEXT_QUERY`/`TERMINATE` protocol).
  - Complex recursion and branching across services can make reasoning/debugging hard.
  - Some async patterns (e.g., `GlobalScope` in file indexing) are risky for lifecycle/error handling.
  - Tool execution is largely centralized; limited policy layer for advanced governance/sandboxing per tool class.

- **Research relevance:**
  - Useful evidence of **single-agent tool orchestration** in OpenAI-compatible API servers.
  - Good case study for **LLM-guided iterative retrieval control loops** in production code.
  - Demonstrates practical **MCP-to-function-call bridging** and mixed native/remote tool routing.
  - Shows tradeoffs between prompt-governed control logic and formal planner/state-machine approaches.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
