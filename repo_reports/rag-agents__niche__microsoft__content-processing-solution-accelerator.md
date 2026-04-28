---
repo_name: microsoft/content-processing-solution-accelerator
url: "https://github.com/microsoft/content-processing-solution-accelerator"
stars: 206
forks: 185
contributors_count: 40
last_commit_date: "2026-04-20T10:01:12+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:47:39.692481+00:00"
model: auto
duration_s: 82.9
clone_size_kb: 41910
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

This repository is an Azure-based document processing pipeline that ingests claim-related files, extracts structured data, runs safety and quality checks, and stores results in Cosmos DB. In practice, users run the `ContentProcessor` and `ContentProcessorWorkflow` services, which process manifest-listed files through extract/map/evaluate/save steps, then produce claim summary and gap analysis outputs. The workflow is event-driven at the service level (queue + workflow executors), but LLM usage is mostly task-specific calls (schema mapping, summarization, RAI classification). The end result is a persisted claim record with per-document processing status, extracted structured fields, confidence signals, summary text, and detected information gaps.

## 2. Agent Framework & Architecture

The code uses a **custom setup on top of Microsoft `agent_framework`** (not CrewAI/LangGraph/AutoGen at runtime in the main flow), confirmed by imports like `from agent_framework import WorkflowBuilder, Executor, ChatMessage` in `src/ContentProcessorWorkflow/src/steps/claim_processor.py:36-45` and `src/ContentProcessor/src/libs/pipeline/handlers/map_handler.py:17`.

Architecture-wise, there are two orchestration layers:

1. A **workflow executor pipeline** (`WorkflowBuilder`) chaining executors: document processing -> optional RAI -> summarization -> gap analysis (`src/ContentProcessorWorkflow/src/steps/claim_processor.py:158-197`).  
2. Inside selected executors/handlers, a **single LLM agent call** is constructed via `AgentBuilder(...).build()` and executed with `agent.run(...)` (`summarize_executor.py:174-193`, `gap_executor.py:173-193`, `rai_executor.py:168-190`, `map_handler.py:236-255`).

There is also a generic **multi-agent group-chat orchestration module** (`GroupChatOrchestrator`) with coordinator/participants/termination logic (`src/ContentProcessorWorkflow/src/libs/agent_framework/groupchat_orchestrator.py:228-1540`), but I did not find production subclasses/usages beyond tests (`test_groupchat_orchestrator_termination.py`), so current shipped workflow behavior is predominantly single-agent-per-step.

## 3. Orchestration Pattern

Closest match: **sequential workflow automation with conditional branching** (not active multi-agent runtime). The control flow is explicit in `WorkflowBuilder` edges:

- `document_processing -> rai_analysis` (if RAI enabled), else `document_processing -> summarizing`, then `summarizing -> gap_analysis` in `src/ContentProcessorWorkflow/src/steps/claim_processor.py:184-197`.

Example control-flow excerpt:
```python
.add_edge(
    source="document_processing",
    target="rai_analysis",
    condition=lambda _: self.app_context.configuration.app_rai_enabled,
)
.add_edge(source="rai_analysis", target="summarizing")
.add_edge(source="document_processing", target="summarizing",
          condition=lambda _: not self.app_context.configuration.app_rai_enabled)
```
(from `src/ContentProcessorWorkflow/src/steps/claim_processor.py:184-196`)

LLM invocation happens *inside* steps rather than through agent-to-agent delegation:
```python
agent = (
    AgentBuilder(agent_client)
    .with_name("Claim Summarization Agent")
    .with_instructions(claim_summarization_prompt)
    .with_temperature(0.1)
    .with_top_p(0.1)
    .build()
)
model_response = await agent.run(ChatMessage(role="user", text=...))
```
(from `src/ContentProcessorWorkflow/src/steps/summarize/executor/summarize_executor.py:174-193`)

## 4. Tools & External Integrations

- **Azure OpenAI via `agent_framework` clients**: client factory and retry wrappers in `src/ContentProcessorWorkflow/src/libs/agent_framework/agent_framework_helper.py:53-497`; LLM agents instantiated in `summarize_executor.py`, `gap_executor.py`, `rai_executor.py`, and `map_handler.py`.
- **Azure AI Content Understanding (REST)**: analyzer create/analyze/poll lifecycle in `src/ContentProcessor/src/libs/azure_helper/content_understanding.py:24-365`.
- **Azure Blob Storage**: manifest and file reads/writes via `AsyncStorageBlobHelper` and `StorageBlobHelper` in `document_process_executor.py:125-174` and `content_process_service.py:83-143`.
- **Azure Queue Storage**: enqueue content-processing jobs in `src/ContentProcessorWorkflow/src/services/content_process_service.py:95-193`.
- **Cosmos DB**: claim/process persistence via repositories and direct service operations in `claim_processor.py:240-317`, `document_process_executor.py:198-290`, `content_process_service.py:70-76`.
- **Pydantic structured output validation**: schema-constrained LLM outputs in `map_handler.py:242-263` and RAI JSON validation in `rai_executor.py:173-193`.
- **No browser automation / shell tools / external web-search tools** wired into agent calls in the main code path.

## 5. Notable Code Walkthrough

- `src/ContentProcessorWorkflow/src/steps/claim_processor.py:123-317`  
  Builds the end-to-end executor graph and handles runtime events (executor invoked/failed/output), while updating claim status in Cosmos; this is the top-level orchestrator for business workflow progression.

- `src/ContentProcessorWorkflow/src/steps/summarize/executor/summarize_executor.py:79-207`  
  Pulls extracted document text from prior processing artifacts, runs a summarization LLM prompt via `AgentBuilder`, and persists summary back to claim records.

- `src/ContentProcessorWorkflow/src/steps/gap_analysis/executor/gap_executor.py:71-221`  
  Loads prompt + YAML rules DSL, calls an LLM for gap detection on processed outputs, and writes identified gaps to the claim process entity.

- `src/ContentProcessor/src/libs/pipeline/handlers/map_handler.py:66-357`  
  Most representative LLM-heavy file: constructs multimodal prompt (text + page images), loads schema dynamically, calls Azure OpenAI with structured response format, and stores parsed extraction + logprobs.

- `src/ContentProcessorWorkflow/src/libs/agent_framework/groupchat_orchestrator.py:228-1282`  
  Implements rich multi-agent group chat mechanics (coordinator selection, tool-call streaming, loop detection, sign-off validation), but appears to be framework infrastructure not currently wired into the primary production workflow.

## 6. Use-Case Mapping

The repository realizes **Workflow Automation** more strongly than `RAG + Agents`: it automates a multi-step claims-content pipeline (ingest -> extract/map/evaluate -> summarize -> gap analysis) with state transitions, persistence, and queue-driven processing. LLMs are used as specialized workers for extraction/summarization/safety classification, but there is no clear retrieval-centric RAG stack (no vector DB retrieval loop) and no active runtime multi-agent team handoff in the main flow. The existing `GroupChatOrchestrator` suggests planned/optional multi-agent capability, but current operational path is predominantly deterministic workflow orchestration with embedded single-agent calls.  
**Better category:** `Workflow Automation`.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear production workflow graph with conditional branching and robust event handling (`claim_processor.py`).
  - Strong Azure integration across Blob/Queue/Cosmos/Content Understanding/OpenAI.
  - Structured-output discipline (Pydantic schemas) improves extraction reliability (`map_handler.py`, `rai_executor.py`).
  - Good operational safeguards in reusable multi-agent infra (timeouts, loop detection, sign-off checks) in `groupchat_orchestrator.py`.
  - Practical multimodal handling (PDF pages converted to images + text context) in `map_handler.py`.

- **Limitations:**
  - Main runtime path is not true coordinated multi-agent collaboration; mostly one LLM call per step.
  - `GroupChatOrchestrator` appears underutilized in production code (primarily tested, not integrated into claim workflow).
  - Prompt-heavy logic and hardcoded instruction blocks may be brittle and difficult to version/control at scale.
  - No evident retrieval layer (vector store/query-time grounding), limiting “RAG” characterization.
  - Some integration logic mixes infrastructure and business concerns, increasing coupling across workflow/executor layers.

- **Research relevance:**
  - Good evidence for **LLM-augmented enterprise workflow automation** rather than emergent multi-agent behavior.
  - Useful case study in combining deterministic orchestration with schema-constrained LLM steps.
  - Demonstrates a reusable but not fully adopted multi-agent orchestration component in real product codebases.
  - Illustrates multimodal extraction pipelines where LLM outputs are post-processed with confidence fusion logic.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
