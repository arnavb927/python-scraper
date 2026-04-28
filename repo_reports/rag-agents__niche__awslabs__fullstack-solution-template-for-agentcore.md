---
repo_name: awslabs/fullstack-solution-template-for-agentcore
url: "https://github.com/awslabs/fullstack-solution-template-for-agentcore"
stars: 471
forks: 140
contributors_count: 22
last_commit_date: "2026-04-19T04:05:26+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 6
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T13:08:43.399078+00:00"
model: auto
duration_s: 102.9
clone_size_kb: 5731
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`awslabs/fullstack-solution-template-for-agentcore` is a deployable full-stack template for running LLM agents on Amazon Bedrock AgentCore with a React frontend, auth, memory, and tool access. A user deploys the CDK/Terraform stack, opens the web chat UI, and sends prompts that are forwarded to an AgentCore Runtime endpoint (`frontend/src/lib/agentcore-client/client.ts`, `infra-cdk/lib/backend-stack.ts`). The backend can be switched between multiple agent implementations (Strands, LangGraph, Claude Agent SDK, AG-UI variants) via config (`infra-cdk/config.yaml`, `infra-cdk/lib/utils/config-manager.ts`). Out of the box, the agent can call a Gateway-hosted Lambda tool and Bedrock AgentCore Code Interpreter, so users get a working “agent + tools” workflow rather than just plain chat.

## 2. Agent Framework & Architecture

Framework usage is **multi-framework**, confirmed in source imports:
- **Strands** (`from strands import Agent`) in `patterns/strands-single-agent/basic_agent.py:15-105`
- **LangGraph/LangChain** (`create_agent`, `AgentCoreMemorySaver`) in `patterns/langgraph-single-agent/langgraph_agent.py:7-58`
- **Claude Agent SDK** (`ClaudeSDKClient`, `AgentDefinition`) in `patterns/claude-agent-sdk-single-agent/agent.py:9-206` and `patterns/claude-agent-sdk-multi-agent/agents/subagents.py:12-52`
- **AG-UI/CopilotKit wrappers** in `patterns/agui-langgraph-agent/agent.py:10-99`

So the upstream “LangGraph, CrewAI” label is partially wrong: LangGraph is present, **CrewAI is not** in runtime code.

Architecturally, this repo is a **patternized runtime template**. Infrastructure chooses one backend pattern via `backend.pattern` (`infra-cdk/config.yaml:7-16`) and builds the corresponding runtime artifact (`infra-cdk/lib/backend-stack.ts:99-223`). Most patterns are single-agent tool-calling agents; the notable multi-agent runtime is `claude-agent-sdk-multi-agent`, where a parent Claude agent is configured with a `Task` tool and subagent definitions (`patterns/claude-agent-sdk-multi-agent/agent.py:101-131`, `patterns/claude-agent-sdk-multi-agent/agents/subagents.py:24-51`).

“Intelligence” mainly lives in:
- system prompts and tool rules (`patterns/*/agent.py`)
- framework-native planners/tool loops (Strands/LangGraph/Claude SDK)
- memory configuration (short-term + optional semantic retrieval) in Strands/LangGraph patterns (`patterns/strands-single-agent/basic_agent.py:32-81`, `patterns/langgraph-single-agent/langgraph_agent.py:34-58`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)** for the actual multi-agent implementation, with a configurable template that can also run single-agent flows.

The parent agent explicitly enables delegation (`Task`) and registers a named subagent set:

```105:131:patterns/claude-agent-sdk-multi-agent/agent.py
    # Build subagent definitions
    subagents = get_subagent_definitions(mcp_servers)

    def _build_options(resume_id: str | None) -> ClaudeAgentOptions:
        return ClaudeAgentOptions(
            mcp_servers=mcp_servers,
            ...
            # Add Task tool for subagent spawning
            agents=subagents,
            resume=resume_id,
            ...
        )
```

The worker agent (`code-analyst`) is separately defined with a specialized prompt/tools/model, which is classic manager-worker specialization:

```24:51:patterns/claude-agent-sdk-multi-agent/agents/subagents.py
    return {
        "code-analyst": AgentDefinition(
            description="Analyzes code output, debugs errors, and explains results...",
            prompt="""You are a code analysis specialist...""",
            tools=[
                "mcp__codeint__execute_code",
                "mcp__codeint__execute_command",
                "mcp__gateway__*",
                "Read",
                "Grep",
                "Glob",
            ],
            model="sonnet",
        ),
    }
```

Control flow is: frontend request -> AgentCore runtime entrypoint -> parent model loop -> optional `Task` delegation to subagent child process -> tool invocations -> streamed events back to frontend (`frontend/src/lib/agentcore-client/parsers/claude-agent-sdk.ts`).

## 4. Tools & External Integrations

- **Amazon Bedrock AgentCore Runtime** (HTTP/SSE agent invocation): wired in runtime entrypoints and client transport (`patterns/*/agent.py`, `frontend/src/lib/agentcore-client/client.ts:46-88`).
- **AgentCore Gateway via MCP** (external tool bus over streamable HTTP): clients in `patterns/strands-single-agent/tools/gateway.py:41-67` and `patterns/langgraph-single-agent/tools/gateway.py:38-68`; gateway infra in `infra-cdk/lib/backend-stack.ts:628-877`.
- **Gateway Lambda tool example** (text analysis): implementation `gateway/tools/sample_tool/sample_tool_lambda.py:40-99`, schema at `gateway/tools/sample_tool/tool_spec.json`.
- **AgentCore Code Interpreter** (sandboxed code + command/file ops): Claude MCP server wrapper `patterns/claude-agent-sdk-multi-agent/code_int_mcp/server.py:19-84`; underlying API client `patterns/claude-agent-sdk-multi-agent/code_int_mcp/client.py:18-103`; LangGraph/Strands wrappers in each pattern’s `tools/code_interpreter.py`.
- **Agent memory services** (short-term and optional semantic/facts retrieval): Strands memory session manager `patterns/strands-single-agent/basic_agent.py:32-81`; LangGraph checkpoint saver `patterns/langgraph-single-agent/langgraph_agent.py:34-58`; memory resource provisioning in `infra-cdk/lib/backend-stack.ts:240-283`.
- **OAuth2/Cognito identity flows** for runtime->gateway and user auth: token decorator and JWT extraction in `patterns/utils/auth.py:18-102`; Cognito + credential provider provisioning in `infra-cdk/lib/backend-stack.ts:879-957` and `:702-789`.
- **Feedback API + DynamoDB** (not an agent tool, but app integration): `infra-cdk/lib/backend-stack.ts:463-626`.

No browser automation (Playwright), terminal-shell agent, or vector DB RAG stack (e.g., Pinecone/pgvector/Chroma) is wired in code.

## 5. Notable Code Walkthrough

- `patterns/claude-agent-sdk-multi-agent/agent.py:36-219` - Main multi-agent runtime entrypoint; sets MCP servers, allowed/disallowed tools, subagent registry, session resume map, and streams Claude events back to AgentCore clients.
- `patterns/claude-agent-sdk-multi-agent/agents/subagents.py:15-52` - Defines specialized subagent roles (currently `code-analyst`) with dedicated prompt/tools/model; this is the clearest MAS logic in the repo.
- `patterns/strands-single-agent/basic_agent.py:84-134` - Canonical single-agent pattern combining model, Gateway MCP client, Code Interpreter, and memory session manager; representative of baseline behavior.
- `infra-cdk/lib/backend-stack.ts:99-223` - Selects and packages the chosen pattern (`backend.pattern`) as runtime artifact; this is what turns the repo into a pluggable architecture rather than a single hardcoded agent.
- `frontend/src/lib/agentcore-client/client.ts:12-88` - Frontend transport/orchestration layer that picks parser by pattern prefix and streams runtime responses, enabling one UI to support different backend agent frameworks.

## 6. Use-Case Mapping

The assigned label **RAG + Agents** is only partially accurate. The code clearly implements agents with tools and memory, but it does **not** implement a standard document RAG pipeline (no corpus ingestion/indexing/retrieval over external knowledge base, no vector store connector path in runtime patterns). The “semantic memory facts” feature is user-memory retrieval, not full RAG over enterprise docs (`patterns/strands-single-agent/basic_agent.py:53-77`, `infra-cdk/lib/backend-stack.ts:248-257`).

A better category for this repository is **Workflow Automation**: it is a production template for orchestrating authenticated agent workflows, tool execution (Gateway + Code Interpreter), runtime deployment, and frontend streaming across multiple interchangeable agent frameworks.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clean pluggable architecture: framework swap via config, not rewrite (`infra-cdk/config.yaml`, `backend-stack.ts`).
  - Strong security posture in baseline: JWT extraction from validated headers, OAuth2 M2M token flow, scoped IAM (`patterns/utils/auth.py`, `infra-cdk/lib/backend-stack.ts`).
  - Real tool orchestration path through MCP Gateway and Code Interpreter, not mock-only demos.
  - Includes true multi-agent runtime variant (parent + delegated subagent) in addition to single-agent baselines.
  - End-to-end fullstack scaffold (infra + runtime + frontend streaming protocol adapters).

- **Limitations:**
  - MAS depth is limited: only one explicit subagent role (`code-analyst`), no complex team topology/debate/swarm.
  - No first-class RAG ingestion/retrieval pipeline despite “facts” memory support.
  - Multi-agent behavior depends on selecting a specific pattern; default config is single-agent (`strands-single-agent`).
  - Minimal representative tooling (single sample Lambda tool) may underrepresent real enterprise integration complexity.
  - Some operational state is in-memory only (e.g., Claude session map), so restarts can break continuity.

- **Research relevance:**
  - Useful evidence of **production-oriented agent platform engineering** (auth, deployment, protocol abstraction).
  - Demonstrates **manager-worker delegation** via Claude SDK subagents in a practical runtime.
  - Good case study for **tool-mediated agency** through MCP and secure external service access.
  - Illustrates tradeoffs between **framework-agnostic templates** and depth of any one MAS paradigm.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
