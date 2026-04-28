---
repo_name: Zettelgarden/Zettelgarden
url: "https://github.com/Zettelgarden/Zettelgarden"
stars: 166
forks: 4
contributors_count: 6
last_commit_date: "2026-04-06T16:48:26+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:50:04.529237+00:00"
model: auto
duration_s: 105.0
clone_size_kb: 38892
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

Zettelgarden is a full-stack personal knowledge management system where users store cards, tasks, entities, and facts, then query and manipulate them through an LLM-powered assistant. In practice, users run the web app (and optionally a Telegram bot) and chat with an assistant that can call backend tools to search notes, create/update cards, manage tasks, and traverse entity/fact links. The backend provides OpenAI-compatible chat completion with function/tool calling, plus background LLM jobs for summarization, entity extraction, and memory updates. The result is an AI-augmented zettelkasten workflow rather than a generic chatbot.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph, LangChain, AutoGen, CrewAI, or LlamaIndex. The implementation is a **custom Go agent loop** built directly on `github.com/sashabaranov/go-openai` (`go-backend/go.mod:30`, `go-backend/services/llms.go:79-184`) with handwritten tool registry and execution logic (`go-backend/services/registry.go:31-100`).

The primary “agent” is a single assistant in `chat_agent` that:
1) builds a system prompt (`go-backend/handlers/chat_agent/prompt.go:11-56`, prompt file at `go-backend/prompts/zettelgarden_assistant.md`),  
2) sends chat+tool requests to the LLM (`go-backend/handlers/chat_agent/streaming.go:225-289`),  
3) executes returned tool calls via a tool registry (`go-backend/handlers/chat_agent/tools_execution.go:13-52`), and  
4) loops until the model returns plain content (`go-backend/handlers/chat_agent/streaming.go:333-381`).

There are also asynchronous LLM **job processors** (entity extraction, summarization, memory, etc.) in `go-backend/services/llmprocessor.go:29-51`, run by a worker pool (`go-backend/services/llmworker.go:33-76`, `274-299`). These are LLM workflows, but not multiple collaborating runtime chat agents.

## 3. Orchestration Pattern

Closest match: **sequential tool-augmented loop (single-agent ReAct/function-calling)**, with secondary **event-driven background workers** for offline jobs.

Control flow in the chat loop is iterative: call LLM → if tool calls exist, execute tools → append tool outputs → call LLM again.

From `go-backend/handlers/chat_agent/streaming.go`:

```273:281:go-backend/handlers/chat_agent/streaming.go
for totalIterations < absoluteMaxLoops {
    totalIterations++
    if loopDetector.GetIteration() >= maxLoopIterations {
        interventionMsg := loopDetector.GetInterventionMessage()
        openaiMessages = append(openaiMessages, openai.ChatCompletionMessage{
            Role:    openai.ChatMessageRoleSystem,
            Content: interventionMsg,
        })
```

```346:356:go-backend/handlers/chat_agent/streaming.go
toolCalls := convertAndBroadcastToolCalls(currentToolCalls, sendEvent)

if err = s.updateAssistantMessageWithToolCalls(assistantMessageID, &currentContent, toolCalls); err != nil {
    return err
}

if err = s.executeAndBroadcastToolCalls(currentToolCalls, userID, conversation.ID, assistantMessageID, model, sendEvent, loopDetector); err != nil {
    return err
}
```

Tool dispatch itself is centralized in the registry:

```64:74:go-backend/services/registry.go
func (tr *ToolRegistry) ExecuteTool(name string, args map[string]interface{}, ctx *ToolContext) (map[string]interface{}, error) {
    if err := ctx.Validate(); err != nil {
        return nil, fmt.Errorf("invalid tool context: %w", err)
    }

    tool, exists := tr.tools[name]
    if !exists {
        return nil, fmt.Errorf("tool %s not found", name)
    }
```

## 4. Tools & External Integrations

- **OpenAI-compatible LLM API**: central request layer in `go-backend/services/llms.go:25-31`, `106-141`, `149-184`; endpoint/model from env vars.
- **Function/tool calling layer**: registry + JSON schema-like tool definitions in `go-backend/services/registry.go:36-53`, `55-62` and registration helpers in `go-backend/services/registration.go:112-127`.
- **Knowledge-base tools (cards/tasks/entities/facts/templates/memory)**: wired in `go-backend/services/registry.go:42-50`, with domain registrations in `go-backend/services/card_tools.go`, `task_tools.go`, `entity_tools.go`, `fact_tools.go`, `memory_tools.go`.
- **Vector/text retrieval via Typesense**: card/entity/fact search paths call Typesense (`go-backend/services/tools/card/card.go:28-53`, `124-149`; `go-backend/services/typesense.go:13-70`).
- **Primary DB (PostgreSQL)**: pervasive SQL access in handlers/services (e.g., `go-backend/services/registry.go:117-129`, `go-backend/services/tools/calendar/calendar.go:16-300`).
- **URL/article ingestion**: readability + HTML-to-markdown in `go-backend/services/tools/article/article.go:13-55`.
- **External calendar integration**: calendar/event listing and card linking in `go-backend/services/calendar_tools.go:55-75`, data ops in `go-backend/services/tools/calendar/calendar.go:61-181`.
- **Telegram interface to same chat agent**: message handling and async response pipeline in `go-backend/telegram/bot.go:150-204`, `247-300`.
- **Background workflow engine**: job queue workers + processor in `go-backend/services/llmworker.go` and `go-backend/services/llmprocessor.go`.

No MCP/browser automation or terminal-control tools were found in the runtime agent path.

## 5. Notable Code Walkthrough

- `go-backend/handlers/chat_agent/streaming.go:225-393` - core runtime agent loop with streaming, tool-call accumulation, loop detection, and iterative re-prompting.
- `go-backend/services/registry.go:31-130` - tool registry abstraction that defines, exposes, executes, and logs callable tools for the LLM.
- `go-backend/services/card_tools.go:46-179` - representative domain-tool registration showing how natural-language tasks map to concrete DB/search operations.
- `go-backend/services/llmprocessor.go:29-369` - asynchronous LLM workflow processor (summarization, entity extraction, memory updates), demonstrating non-interactive automation.
- `go-backend/prompts/zettelgarden_assistant.md:12-139` - operational policy/prompt where most assistant behavior and tool-use strategy are encoded.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** does **not** match the codebase well. The repository does not implement browser automation agents (Playwright/Browserbase) or terminal-command agents; instead, it implements a productivity assistant that automates knowledge workflows (search, extraction, linking, summarizing, task management) over a personal knowledge base.

A better classification is **Workflow Automation** (with strong RAG-like retrieval elements via Typesense semantic/text search). The assistant orchestrates internal tools and backend services to complete user goals, but not by operating a browser or shell on the user’s behalf.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong production-style tool-calling loop with retries, loop detection, streaming, and message persistence (`chat_agent` + `tool_retry`).
  - Broad actionable tool surface (cards/tasks/entities/facts/calendar/articles/memory) unified under one registry.
  - Clear separation between interactive chat orchestration and offline job workflows.
  - Real integration stack (Typesense, SQL, Telegram, calendar/article ingest), not a toy demo.

- **Limitations:**
  - Not truly multi-agent at runtime; mostly a single assistant with tools.
  - Some async processor paths are incomplete/placeholders (e.g., chat job placeholder, file extraction marked pending S3 integration in `llmprocessor.go`).
  - Heavy prompt-logic coupling; behavior depends on long prompt instructions rather than explicit planner policy modules.
  - Tool schema/registration is large and partly duplicated (legacy vs v2 feature-flag paths), increasing maintenance complexity.

- **Research relevance:**
  - Useful evidence for **single-agent tool orchestration** in real applications.
  - Good case study of **LLM + workflow automation** over structured knowledge stores.
  - Demonstrates practical safeguards (loop caps, retries, status tracking, worker supervision) for agent reliability.
  - Less suitable as evidence of emergent multi-agent coordination or agent societies.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
