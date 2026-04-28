---
repo_name: 2FastLabs/agent-squad
url: "https://github.com/2FastLabs/agent-squad"
stars: 7587
forks: 713
contributors_count: 31
last_commit_date: "2026-04-17T14:41:47+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T12:00:17.261075+00:00"
model: auto
duration_s: 98.3
clone_size_kb: 67858
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`agent-squad` is a dual Python/TypeScript framework for routing a user request to one of multiple specialized AI agents, then managing memory, streaming, and tool calls around that choice. A user typically instantiates `AgentSquad`, registers several agents (e.g., Bedrock/Anthropic/OpenAI/Lambda/Lex/etc.), and calls `route_request`/`routeRequest` to get a response from the selected agent (`python/src/agent_squad/orchestrator.py:23-275`, `typescript/src/orchestrator.ts:188-502`). The main problem it solves is multi-agent coordination in production-style conversational systems: intent classification, per-agent chat history, and optional nested team patterns (chain/supervisor). It also supports RAG augmentation by attaching retrievers to LLM agents (`python/src/agent_squad/agents/bedrock_llm_agent.py:115-125`).

## 2. Agent Framework & Architecture

This repo is **not** LangGraph/LangChain/CrewAI/AutoGen-first orchestration. It is a **custom orchestration framework** (`AgentSquad`) with adapters to external LLM/provider SDKs: AWS Bedrock (`boto3`), Anthropic SDK, OpenAI SDK, and optional Strands SDK integration (`python/src/agent_squad/agents/strands_agent.py:13-20`). The upstream “CrewAI” label does not match the actual imports/runtime structure.

Architecture is hub-and-spoke: `AgentSquad` owns (1) agent registry, (2) classifier, (3) chat storage, and (4) request routing lifecycle. Classification is itself LLM-driven (Bedrock/Anthropic/OpenAI classifier classes) and uses a generated system prompt containing agent descriptions and history to pick one agent ID plus confidence (`python/src/agent_squad/classifiers/classifier.py:42-205`, `python/src/agent_squad/classifiers/bedrock_classifier.py:47-149`).

Agent implementations share a base `Agent` interface (`process_request`) and include both single-agent adapters (BedrockLLM, Anthropic, OpenAI, Lambda, Lex, Comprehend, Bedrock Flows/Inline) and composite agents (`ChainAgent`, `SupervisorAgent`) (`python/src/agent_squad/agents/agent.py:232-303`, `python/src/agent_squad/agents/chain_agent.py:12-67`, `python/src/agent_squad/agents/supervisor_agent.py:58-307`). “Intelligence” lives in a few places: classifier prompts for routing, per-agent system prompts, and tool-calling loops that recursively execute tool actions until final response (`python/src/agent_squad/agents/bedrock_llm_agent.py:188-357`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker orchestration**, with optional **sequential pipelines**.

- Top-level hierarchy: `AgentSquad` classifies then dispatches to one selected agent.
- Nested hierarchy: `SupervisorAgent` uses a lead LLM agent plus a `send_messages` tool to delegate to team agents in parallel, then aggregate results.
- Optional sequential mode: `ChainAgent` forwards output text from one agent to the next.

Control flow excerpt (top-level route/classify/dispatch):
`python/src/agent_squad/orchestrator.py:244-274,111-121,95-107`
```python
async def route_request(...):
    classifier_result = await self.classify_request(user_input, user_id, session_id)
    ...
    return await self.agent_process_request(...)

classifier_result = await self.measure_execution_time(
    "Classifying user intent",
    lambda: self.classifier.classify(user_input, chat_history)
)
...
response = await selected_agent.process_request(user_input, user_id, session_id, ...)
```

Control flow excerpt (supervisor delegating parallel sub-agent work):
`python/src/agent_squad/agents/supervisor_agent.py:242-266`
```python
tasks = [
    asyncio.create_task(asyncio.to_thread(self.send_message, agent, message.get('content'),
        self.user_id, self.session_id, self.additional_params))
    for agent in self.team
    for message in messages
    if agent.name == message.get('recipient')
]
responses = await asyncio.gather(*tasks)
return ''.join(responses)
```

## 4. Tools & External Integrations

- **LLM providers**
  - AWS Bedrock Runtime (`boto3.client("bedrock-runtime")`) in Bedrock agent/classifier (`python/src/agent_squad/agents/bedrock_llm_agent.py:45-47`, `python/src/agent_squad/classifiers/bedrock_classifier.py:34`).
  - Anthropic SDK (`Anthropic`, `AsyncAnthropic`) (`python/src/agent_squad/agents/anthropic_agent.py:4-5,57-59`).
  - OpenAI SDK (`OpenAI`) (`python/src/agent_squad/agents/openai_agent.py:3,41`).

- **RAG**
  - Amazon Bedrock Knowledge Bases retriever via `bedrock-agent-runtime` retrieve API (`python/src/agent_squad/retrievers/amazon_kb_retriever.py:24-47`).
  - Retrievers are injected into agents and appended to system prompt context (`python/src/agent_squad/agents/bedrock_llm_agent.py:121-124`, similar in `anthropic_agent.py:117-120` and `openai_agent.py:110-113`).

- **Agent tool-calling runtime**
  - Custom `AgentTool` / `AgentTools` schema + execution layer; converts tool specs for Bedrock/Anthropic/OpenAI and handles recursive tool loops (`python/src/agent_squad/utils/tool.py:79-320`, `python/src/agent_squad/agents/bedrock_llm_agent.py:212-357`).

- **AWS service-agent integrations**
  - Lambda invocation agent (`python/src/agent_squad/agents/lambda_agent.py:30,92`).
  - Amazon Lex V2 runtime agent (`python/src/agent_squad/agents/lex_bot_agent.py:31,56`).
  - Amazon Comprehend filter agent (`python/src/agent_squad/agents/comprehend_filter_agent.py:34-39,125-137`).
  - Bedrock Inline Agent / Bedrock Flows invocation (`python/src/agent_squad/agents/bedrock_inline_agent.py:83-84,230`, `python/src/agent_squad/agents/bedrock_flows_agent.py:32-35,83`).

- **Storage backends**
  - In-memory default storage plus DynamoDB and SQL (libSQL/Turso) adapters (`python/src/agent_squad/orchestrator.py:50`, `python/src/agent_squad/storage/dynamodb_chat_storage.py:21-23`, `python/src/agent_squad/storage/sql_chat_storage.py:4,24-27`).

- **MCP (via Strands integration)**
  - Optional MCP clients are started and their tools exposed when using `StrandsAgent` (`python/src/agent_squad/agents/strands_agent.py:39,73-90`).

## 5. Notable Code Walkthrough

- `python/src/agent_squad/orchestrator.py:23-289`  
  Central runtime coordinator: registers agents, runs classifier, dispatches selected agent, handles streaming/non-streaming responses, and persists chat memory.

- `python/src/agent_squad/classifiers/classifier.py:42-205`  
  Defines the router prompt template and placeholder injection (`AGENT_DESCRIPTIONS`, `HISTORY`), showing that agent selection is prompt-driven rather than rule-based.

- `python/src/agent_squad/agents/supervisor_agent.py:84-175,242-307`  
  Implements manager-agent behavior: configures a delegation tool (`send_messages`), injects team roster into prompt, and lets a lead LLM coordinate sub-agents.

- `python/src/agent_squad/agents/chain_agent.py:20-67`  
  Implements deterministic sequential pipeline orchestration where each agent’s text output becomes the next agent’s input.

- `python/src/agent_squad/agents/bedrock_llm_agent.py:115-125,188-227,333-357`  
  Shows RAG context injection + recursive tool-use loop; this is where single-agent execution can become iterative tool-driven workflow.

## 6. Use-Case Mapping

The repo does support **RAG + Agents** technically (retriever interface + Amazon KB retriever + prompt augmentation in LLM agents). However, the dominant core is broader **multi-agent workflow routing/orchestration**: classifier-based agent dispatch, manager/team delegation (`SupervisorAgent`), and chain pipelines (`ChainAgent`) across many service-specific agent types. So the assigned label is partially right, but **Workflow Automation** is a better primary category for the repository as a whole, with RAG as an optional capability.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Practical multi-agent runtime patterns in one framework: router, supervisor-team, and chain orchestration.
  - Strong provider breadth (Bedrock, Anthropic, OpenAI, AWS service agents) with consistent `Agent` abstraction.
  - Built-in chat memory pluggability (in-memory, DynamoDB, SQL/libSQL) suitable for production workflows.
  - Unified tool-calling abstraction that normalizes tool schemas across providers.
  - Python and TypeScript parity enables comparative implementation study.

- **Limitations:**
  - Heavy AWS coupling in defaults (Bedrock classifier is default path), reducing out-of-box provider neutrality.
  - Supervisor logic uses prompt instructions for coordination rather than explicit task graph/planner state, so behavior may be brittle.
  - Limited built-in evaluation/guardrail logic for delegation quality, conflict resolution, or tool-call safety policy beyond provider mechanisms.
  - Some integrations are thin wrappers (e.g., external service agents) with limited higher-level planning semantics.
  - No explicit global shared blackboard/graph scheduler; coordination is mostly agent-prompt mediated.

- **Research relevance:**
  - Evidence of **hierarchical multi-agent orchestration** in applied frameworks (manager LLM delegating to team agents).
  - Evidence of **LLM-as-router** intent classification patterns for dynamic agent selection.
  - Evidence of **tool-recursive agent loops** (LLM tool calls + execution + continuation) in production-style SDK wrappers.
  - Useful case study for cross-language MAS framework design (Python/TypeScript feature parity).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
