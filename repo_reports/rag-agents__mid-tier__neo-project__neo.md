---
repo_name: neo-project/neo
url: "https://github.com/neo-project/neo"
stars: 3535
forks: 1046
contributors_count: 82
last_commit_date: "2026-04-18T15:27:38+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 6
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T12:28:57.479138+00:00"
model: auto
duration_s: 63.0
clone_size_kb: 4777
uses_mas: no
final_use_case: None
---
## 1. Overview

`neo-project/neo` is the core C# protocol/runtime library for the NEO blockchain, not an LLM application. In practice, developers run this code as the blockchain engine inside node software (the repo itself points to `neo-node` for the CLI process), and they get block validation, transaction relay, smart-contract execution, and persistent chain state management (`README.md:109-136`, `src/Neo/NeoSystem.cs:33-79`). The runtime wires together actor-based services (`Blockchain`, `LocalNode`, `TaskManager`, `TxRouter`) plus storage and plugin hooks (`src/Neo/NeoSystem.cs:149-156`). It solves distributed ledger synchronization and contract execution for NEO networks rather than AI task automation.

## 2. Agent Framework & Architecture

No LLM-agent framework is used. There are no LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex/OpenAI-style dependencies; the main project references Akka and blockchain/crypto libraries instead (`src/Neo/Neo.csproj:9-18`).

Architecture is an actor-based blockchain runtime (Akka.NET), not agentic AI. `NeoSystem` bootstraps core actors and shared state (`src/Neo/NeoSystem.cs:149-153`), while `Blockchain` processes inventory events and persists blocks (`src/Neo/Ledger/Blockchain.cs:345-382`, `src/Neo/Ledger/Blockchain.cs:410-481`). `TaskManager` schedules P2P sync tasks across peers (`src/Neo/Network/P2P/TaskManager.cs:29-33`, `src/Neo/Network/P2P/TaskManager.cs:358-416`), and `TransactionRouter` parallelizes state-independent preverification (`src/Neo/Ledger/TransactionRouter.cs:26-37`).

The “intelligence” here is protocol logic (validation rules, mempool policy, persistence order, consensus/network handling), not prompts/planners/tool-calling.

## 3. Orchestration Pattern

Closest match: **event-driven actor system** (Akka message passing), not multi-agent LLM orchestration.

Control flow example 1: system composition and message topology:
- `NeoSystem` creates actors for chain, networking, tasks, and tx routing (`src/Neo/NeoSystem.cs:149-153`).
- `Blockchain` forwards tx preverify work to `TxRouter` and handles callback messages (`src/Neo/Ledger/Blockchain.cs:370-372`, `src/Neo/Ledger/Blockchain.cs:402-405`).

Control flow example 2: event-loop style dispatch in actors:
- `Blockchain.OnReceive` branches on message types (`Initialize`, `Import`, `Header[]`, `Transaction`, `Reverify`, etc.) (`src/Neo/Ledger/Blockchain.cs:345-381`).
- `TaskManager.OnReceive` similarly reacts to peer/task/persist events and timer ticks (`src/Neo/Network/P2P/TaskManager.cs:152-187`).

## 4. Tools & External Integrations

This repo exposes **blockchain/node integrations**, not LLM tools.

- **Akka actor runtime** for orchestration and mailbox/router policies (`src/Neo/NeoSystem.cs:50-54`, `src/Neo/Ledger/TransactionRouter.cs:36-37`).
- **P2P networking** (`LocalNode`, message commands like `GetData`, `GetHeaders`, `Mempool`) (`src/Neo/Network/P2P/TaskManager.cs:379-415`).
- **Storage providers / snapshots** via `IStoreProvider` and `StoreFactory` (`src/Neo/NeoSystem.cs:127-129`, `src/Neo/NeoSystem.cs:305-308`).
- **Plugin loading/extensibility** via dynamic assembly discovery in `Plugins` directory (`src/Neo/Plugins/Plugin.cs:37-39`, `src/Neo/Plugins/Plugin.cs:204-229`).
- **On-chain oracle native contract** for smart-contract oracle requests/responses (blockchain feature, not LLM retrieval) (`src/Neo/SmartContract/Native/OracleContract.cs:31-35`, `src/Neo/SmartContract/Native/OracleContract.cs:221-286`).

No MCP servers, LLM APIs, vector DBs, embeddings, browser automation, or RAG pipeline wiring were found.

## 5. Notable Code Walkthrough

- `src/Neo/NeoSystem.cs:33-156` - Defines the top-level node runtime container; instantiates core actors, storage, mempool, genesis block, and plugin lifecycle hooks.
- `src/Neo/Ledger/Blockchain.cs:345-481` - Central event handler for chain state transitions; validates incoming inventory, persists blocks, executes smart-contract triggers, and publishes events.
- `src/Neo/Network/P2P/TaskManager.cs:99-150` - Coordinates peer synchronization tasks and conflict handling across remote sessions, including header/block scheduling logic.
- `src/Neo/Ledger/TransactionRouter.cs:19-37` - Lightweight worker actor for parallel transaction preverification before handing results back to `Blockchain`.
- `src/Neo/Plugins/Plugin.cs:169-229` - Dynamic plugin discovery/loading mechanism; explains how extra node capabilities are integrated at runtime.

## 6. Use-Case Mapping

The assigned category **“RAG + Agents” is incorrect** for this repository. The codebase implements a blockchain protocol engine with actor-based networking and smart-contract execution; it has no retrieval-augmented generation, no LLM calls, and no runtime collaboration among LLM agents (`src/Neo/Neo.csproj:9-18`, `src/Neo/NeoSystem.cs:149-153`).  
A better category from the allowed list is **`None`** (it is infrastructure/protocol software rather than an AI-agent application).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Mature, explicit actor-based concurrency model for node internals (`src/Neo/NeoSystem.cs:50-54`).
  - Clear separation of concerns across ledger, P2P, contracts, wallets, persistence.
  - Strong extensibility via plugin system with error policies (`src/Neo/Plugins/Plugin.cs:76-83`, `src/Neo/Plugins/Plugin.cs:253-290`).
  - Detailed transaction/block verification and persistence pipeline (`src/Neo/Ledger/Blockchain.cs:220-335`, `src/Neo/Ledger/Blockchain.cs:410-481`).
  - Large unit-test surface across modules (tests folder breadth).

- **Limitations:**
  - No LLM-agent components, so irrelevant for studying prompting/planning/tool-using AI agents.
  - No RAG stack (no embedding/index/retrieval abstractions).
  - No natural-language interface layer in this repo (CLI/node app split into other repos).
  - Actor/event complexity can be hard to reason about without Akka expertise.

- **Research relevance:**
  - Useful evidence for **event-driven distributed system orchestration** (non-LLM actors).
  - Useful for **plugin-based extensibility and fault-policy handling** in long-running nodes.
  - Useful for **protocol-level validation/persistence workflows** under concurrent network input.
  - Not suitable evidence for multi-agent LLM runtime behavior.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
