---
repo_name: memodb-io/Acontext
url: "https://github.com/memodb-io/Acontext"
stars: 3343
forks: 313
contributors_count: 10
last_commit_date: "2026-04-21T10:24:48+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 7
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T11:36:21.894495+00:00"
model: auto
duration_s: 125.8
clone_size_kb: 40194
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

Acontext is a production system that adds persistent memory and task/skill tracking around AI-agent conversations, rather than a single chat assistant. A user interacts through the API/SDKs by storing session messages, and backend workers automatically extract/update tasks and learn reusable “skills” from completed work (`src/server/api/go/internal/modules/service/session.go:418-433`, `src/server/core/acontext_core/service/session_message.py:28-121`). The core runtime then runs LLM-driven loops to manage task state and distill long-term skill knowledge into a learning space (`src/server/core/acontext_core/llm/agent/task.py:118-310`, `src/server/core/acontext_core/llm/agent/skill_learner.py:45-209`). In practice, users get structured task timelines, learned skill files, and session-linked memory that can be reused across future agent runs.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph, CrewAI, AutoGen, or LlamaIndex in the runtime path. The agent stack is a **custom orchestration layer** built on FastAPI + RabbitMQ + custom tool-calling loops over OpenAI/Anthropic SDK clients (`src/server/core/acontext_core/llm/complete/__init__.py:13-51`, `src/server/core/acontext_core/llm/complete/openai_sdk.py:53-61`, `src/server/core/acontext_core/llm/complete/anthropic_sdk.py:107-109`).

The architecture has two coordinated LLM agents plus a distillation stage:  
1) **Task Management Agent** (`task_agent_curd`) analyzes message buffers, updates tasks/progress/preferences via tool calls, and emits learning events (`src/server/core/acontext_core/llm/agent/task.py:165-187`, `261-297`).  
2) **Skill Distillation + Skill Learner Agent** first distills finished-task context (`process_context_distillation`) and then runs a second agent loop that edits/creates skill files (`src/server/core/acontext_core/service/controller/skill_learner.py:28-147`, `150-195`; `src/server/core/acontext_core/llm/agent/skill_learner.py:85-179`).

“Intelligence” primarily lives in explicit system prompts and tool schemas, not in a graph DSL: the task/skill prompts contain decision policies and tool protocol (`src/server/core/acontext_core/llm/prompt/task.py:10-104`, `src/server/core/acontext_core/llm/prompt/skill_learner.py:17-147`), while tool pools constrain agent actions (`src/server/core/acontext_core/llm/tool/task_tools.py:11-28`, `src/server/core/acontext_core/llm/tool/skill_learner_tools.py:51-69`).

## 3. Orchestration Pattern

Closest pattern: **event-driven hierarchical pipeline** (manager-worker via queues), with each worker running a **sequential tool-calling loop** internally.

Control flow is MQ-driven across stages: API publishes session-message events, core consumer processes buffered messages, task agent may publish learning events, then distill consumer publishes to skill-agent queue, and skill agent processes serialized updates with Redis locking (`src/server/api/go/internal/modules/service/session.go:418-433`, `src/server/core/acontext_core/service/session_message.py:28-85`, `src/server/core/acontext_core/service/skill_learner.py:30-107`, `116-205`).

```130:140:src/server/core/acontext_core/service/skill_learner.py
_l = await check_redis_lock_or_set(
    body.project_id,
    lock_key,
    ttl_seconds=DEFAULT_CORE_CONFIG.skill_learn_lock_ttl_seconds,
)
if not _l:
    await push_skill_learn_pending(
        body.project_id, body.learning_space_id, body.model_dump_json()
    )
```

```183:195:src/server/core/acontext_core/llm/agent/task.py
r = await llm_complete(
    system_prompt=TaskPrompt.system_prompt(),
    history_messages=_messages,
    tools=json_tools,
    prompt_kwargs=TaskPrompt.prompt_kwargs(),
)
llm_return, eil = r.unpack()
...
if not llm_return.tool_calls:
    break
```

This is not peer-to-peer swarm behavior; agents do not negotiate directly. They are chained by queue routing keys and state transitions.

## 4. Tools & External Integrations

- **LLM providers (OpenAI/Anthropic/mock):** selected via config and called through custom wrappers (`src/server/core/acontext_core/llm/complete/__init__.py:13-33`, `openai_sdk.py:53-61`, `anthropic_sdk.py:99-109`).
- **RabbitMQ event bus:** central orchestration for session and learning pipelines (`src/server/core/acontext_core/infra/async_mq.py:733-745`; core consumers in `service/session_message.py` and `service/skill_learner.py`; API publisher `src/server/api/go/internal/infra/queue/rabbitmq.go:224-239`).
- **Redis locks/queues/cache:** session and learning locks, pending-context queues, and message-part caching (`src/server/core/acontext_core/service/session_message.py:73-85`, `src/server/core/acontext_core/service/skill_learner.py:127-143`; `src/server/api/go/internal/modules/service/session.go:602-714`).
- **PostgreSQL + ORM layers:** persistent tasks/messages/learning-space/sandbox logs (SQLAlchemy/GORM paths include `src/server/core/acontext_core/service/data/*.py`, `src/server/api/go/internal/modules/repo/*`).
- **S3/object storage:** message parts and sandbox file transfer (`src/server/api/go/internal/modules/service/session.go:371-384`, `src/server/core/acontext_core/infra/sandbox/backend/cf.py:334-339`, `367-379`).
- **Sandbox terminal execution (Cloudflare Worker backend):** shell command exec and file upload/download APIs (`src/server/core/routers/sandbox.py:85-138`, `src/server/core/acontext_core/service/data/sandbox.py:262-311`, `src/server/core/acontext_core/infra/sandbox/backend/cf.py:264-295`).

No direct MCP-server integration is evident in the runtime code.

## 5. Notable Code Walkthrough

- `src/server/core/acontext_core/llm/agent/task.py:118-310`  
  Implements the task agent loop: builds prompt context, runs tool-calling iterations, mutates task state, and emits learning/distillation MQ events.

- `src/server/core/acontext_core/service/skill_learner.py:30-213`  
  Defines two RabbitMQ consumers (distill and skill-agent), including Redis lock serialization, retry/retrigger behavior, and session status transitions.

- `src/server/core/acontext_core/service/controller/skill_learner.py:28-147`  
  Runs a dedicated LLM distillation step over completed task data/messages and transforms output into `SkillLearnDistilled` payloads for downstream skill updates.

- `src/server/core/acontext_core/llm/agent/skill_learner.py:45-209`  
  Executes the skill-learning agent loop with tool calls that read/write skill files; also drains queued contexts mid-run and extends iteration budget.

- `src/server/api/go/internal/modules/service/session.go:418-433`  
  API-side trigger point where newly stored messages are published to MQ, initiating the core agentic processing pipeline.

## 6. Use-Case Mapping

The repository includes sandbox command execution APIs, so it has some browser/terminal-adjacent infrastructure (`src/server/core/routers/sandbox.py:85-99`, `src/server/core/acontext_core/service/data/sandbox.py:262-307`). However, the **main agentic behavior** is not autonomous browser/terminal operation; it is workflow-oriented post-processing of conversation streams into tasks and long-term memory skills via asynchronous queues and multi-stage LLM workers. So the upstream “Browser / Terminal Use” label is secondary here.

A better primary category is **Workflow Automation**: message ingestion -> task extraction/update -> distillation -> skill-writing automation across services and queues (`session_message.py`, `llm/agent/task.py`, `service/skill_learner.py`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-stage agent pipeline with explicit queue boundaries and retry/lock semantics.
  - Strong prompt/tool contract design; system prompts encode concrete operational policies.
  - Practical production concerns handled (timeouts, DLX queues, status transitions, telemetry fields).
  - Distinguishes short-term task tracking from long-term skill memory, which is architecturally clean.
  - Supports multiple LLM backends behind a unified completion interface.

- **Limitations:**
  - No declarative graph planner/visual state machine; orchestration logic is spread across consumers/services.
  - Agents are tightly coupled to proprietary data schemas and DB side effects, reducing portability.
  - Skill quality control relies heavily on prompt behavior; limited explicit verifier/evaluator agents.
  - Security TODO remains around KEK transmission through MQ payloads (`session.go:424-427`).
  - “Multi-agent” is pipeline-style, not collaborative reasoning among specialized peer agents.

- **Research relevance:**
  - Good real-world example of event-driven multi-agent coordination over message queues.
  - Demonstrates tool-augmented LLM agents with persistent memory writing/editing actions.
  - Useful evidence for studying reliability patterns (locks, retries, dead-letter queues) in MAS backends.
  - Illustrates how agent memory distillation can be decoupled from primary task-execution loops.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
