---
repo_name: Azure-Samples/microsoft-foundry-baseline
url: "https://github.com/Azure-Samples/microsoft-foundry-baseline"
stars: 190
forks: 104
contributors_count: 14
last_commit_date: "2026-04-15T17:31:53+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:48:19.464427+00:00"
model: auto
duration_s: 84.1
clone_size_kb: 11332
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a reference architecture plus sample implementation for deploying a Microsoft Foundry-backed chat application on Azure, with strong enterprise infrastructure defaults (network isolation, managed identity, private endpoints, monitoring). What a user actually runs is an ASP.NET web app (`website/chatui`) that exposes chat endpoints and forwards prompts to a pre-provisioned Foundry agent. The deployed experience is a browser chat UI that creates a conversation, sends messages, and displays model responses. The agent itself is configured separately (via JSON/CLI) and can use Bing grounding for fresh web-backed answers.

## 2. Agent Framework & Architecture

The runtime agent framework is **Microsoft Foundry Agent Service via the `Microsoft.Agents.AI.Foundry` .NET SDK**, not LangGraph/CrewAI/AutoGen/LangChain. This is confirmed by imports and package usage in `website/chatui/Controllers/ChatController.cs:1-4`, `website/chatui/Configuration/FoundryAgentResolver.cs:1-4`, and `website/chatui/chatui.csproj:12-13`.

Architecture is a **single hosted agent invocation pattern**: the web app resolves one Foundry agent by `(AIAgentId, AIAgentVersion)`, creates/uses a conversation session, and calls `RunAsync` on that agent (`website/chatui/Configuration/FoundryAgentResolver.cs:24-36`, `website/chatui/Controllers/ChatController.cs:25-31`). The “intelligence” (instructions + tool definitions + model binding) is externalized in agent definition JSON (`agents/chat-with-bing.json:5-24`) and persisted into Foundry via CLI workflow (documented in `README.md:237-260`).

Infra code provisions the agent host and dependencies (Cosmos DB, Storage, AI Search, Bing connection) so the Foundry project can run agents with memory/tooling (`infra-as-code/bicep/ai-foundry-project.bicep:177-212`, `infra-as-code/bicep/ai-agent-service-dependencies.bicep:33-73`).

## 3. Orchestration Pattern

Closest match: **sequential (single-agent request/response)**, not multi-agent coordination.

Control flow is linear from UI -> API -> Foundry agent execution:
- `Index.cshtml` creates a conversation then posts each user message to `/chat/responses/{conversationId}` (`website/chatui/Views/Home/Index.cshtml:183-234`).
- Controller resolves one agent and runs it in that session (`website/chatui/Controllers/ChatController.cs:25-31`).

Example flow excerpt (`website/chatui/Controllers/ChatController.cs:25-31`):
```csharp
FoundryAgent agent = agentResolver.GetAgent();
var innerAgent = agent.GetService<ChatClientAgent>()!;
var session = await innerAgent.CreateSessionAsync(conversationId);
var response = await agent.RunAsync(message, session);
return Ok(new { data = response.ToString() });
```

Agent resolution excerpt (`website/chatui/Configuration/FoundryAgentResolver.cs:30-33`):
```csharp
var name = _options.CurrentValue.AIAgentId;
var version = _options.CurrentValue.AIAgentVersion;
var agent = _projectClient.AsAIAgent(new AgentReference(name, version));
```

## 4. Tools & External Integrations

- **Microsoft Foundry Agent Service API**: web app constructs `AIProjectClient` and resolves `FoundryAgent` (`website/chatui/Program.cs:13-19`, `website/chatui/Configuration/FoundryAgentResolver.cs:24-36`).
- **Bing Grounding tool**: agent definition includes `bing_grounding` tool with connection ID (`agents/chat-with-bing.json:8-20`), and project-side Bing connection is provisioned in Bicep (`infra-as-code/bicep/ai-foundry-project.bicep:191-212`).
- **Model connection in Foundry project**: agent JSON expects a model connection name (`agents/chat-with-bing.json:6`), set during provisioning workflow (`README.md:248-255`).
- **Conversation/thread persistence backend (Foundry dependencies)**: Cosmos DB for thread/agent storage, Storage for binaries/knowledge artifacts, AI Search for vector/file search support (`infra-as-code/bicep/ai-agent-service-dependencies.bicep:33-63`, `infra-as-code/bicep/ai-foundry-project.bicep:102-185`).
- **Observability**: Application Insights connected to Foundry project and web app diagnostics (`infra-as-code/bicep/ai-foundry-project.bicep:155-175`, `infra-as-code/bicep/web-app.bicep:246-283`).

No MCP servers, Playwright browser automation, or shell-executing tools are implemented in the runtime app code.

## 5. Notable Code Walkthrough

- `website/chatui/Controllers/ChatController.cs:18-43` - Core runtime entrypoint: creates conversation IDs and routes each user message into a Foundry agent session via `RunAsync`; this is the actual agent invocation path.
- `website/chatui/Configuration/FoundryAgentResolver.cs:10-36` - Lazy, cached resolver for a specific deployed Foundry agent `(id, version)`; important because the app does not build agents dynamically.
- `agents/chat-with-bing.json:1-30` - Canonical agent definition (instructions, model slot, Bing grounding tool); this is where behavior/tooling are declared.
- `infra-as-code/bicep/ai-foundry-project.bicep:88-213` - Provisions Foundry project connections and capability host (`Agents`) and wires storage/thread/vector/Bing connections required by agent service.
- `infra-as-code/bicep/web-app.bicep:213-227` - Injects `AIProjectEndpoint`, `AIAgentId`, and `AIAgentVersion` into app settings, which binds deployment-time agent identity to runtime calls.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** appears inaccurate for this codebase. The browser here is just a chat frontend; the agent does not drive a browser, run terminal commands, or execute computer-use actions. Instead, the repo implements a **deployed chat workflow** where an API calls a preconfigured Foundry agent with web grounding, plus extensive infrastructure automation around that flow.

Better category: **Workflow Automation** (with some overlap with RAG + Agents due grounding/search dependencies).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong production-oriented Azure architecture (private networking, managed identities, diagnostics) alongside agent runtime.
  - Clear separation between agent definition (`agents/*.json`) and app runtime invocation (`chatui`).
  - Explicit provisioning of agent-service dependencies (Cosmos/Storage/AI Search/Bing) in IaC.
  - Simple and understandable end-to-end chat path, good for reproducible baseline deployments.
  - Versioned agent targeting via app settings enables controlled rollout.

- **Limitations:**
  - No true multi-agent runtime orchestration (no planner-worker/supervisor graph/swarm).
  - App only calls one configured agent; no dynamic routing or policy-based tool gating in app layer.
  - Security TODO notes conversation ID trust issue in controller (`ChatController.cs:16-17`).
  - Agent creation/update lifecycle is external/manual (CLI steps), not integrated into app control plane.
  - Minimal application-layer resilience/guardrails (basic error path in UI/API).

- **Research relevance:**
  - Useful evidence of **single-agent enterprise deployment patterns** (agent-as-service + secure infra), not MAS behavior.
  - Illustrates how agent capabilities are operationalized through cloud resource wiring and RBAC.
  - Demonstrates practical decoupling of agent config/versioning from frontend/API code.
  - Good reference for studying infrastructural constraints around production LLM agent hosting.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
