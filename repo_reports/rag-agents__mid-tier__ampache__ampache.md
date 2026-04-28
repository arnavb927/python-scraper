---
repo_name: ampache/ampache
url: "https://github.com/ampache/ampache"
stars: 3795
forks: 603
contributors_count: 171
last_commit_date: "2026-04-20T10:20:58+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 6
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T12:27:49.613870+00:00"
model: auto
duration_s: 95.0
clone_size_kb: 44009
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`ampache/ampache` is a PHP web application for self-hosted audio/video streaming, library management, and metadata-driven browsing rather than an AI agent system. A user deploys it on a web server (with PHP + MySQL/MariaDB), scans media catalogs, and then accesses playback, playlists, stats, and APIs through the web UI and compatible clients (`README.md`, `composer.json`). The runtime starts from web entrypoints like `public/index.php`, which bootstraps DI/config and dispatches request actions to handler classes (`public/index.php:26-38`, `src/Config/Init.php:35-40`). The project also includes CLI/admin workflows (e.g., websocket runner) and many service integrations for media metadata/art retrieval.

## 2. Agent Framework & Architecture

No LLM agent framework is present. I found no runtime use of LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, OpenAI/Anthropic SDKs, embedding/vector DBs, or prompt orchestration in dependencies (`composer.json:39-81`) or source-level imports/search. The string `agent` appears in this repo mainly as **user-agent / playback client agent** telemetry fields (e.g., stream history), not autonomous AI agents (`src/Repository/IpHistoryRepository.php:68-78`, `src/Repository/Model/Song.php:983-1026`).

Architecture is a modular PHP web app: request comes in through entry scripts, app bootstraps from DI, then action handlers are selected and executed. `ApplicationRunner` reads an `action` request key, resolves a handler class from a map, executes it with gatekeeping, and emits response (`src/Module/Application/ApplicationRunner.php:67-110`). Core behavior/“intelligence” lives in deterministic business logic classes (catalog scanning, metadata lookup, plugin hooks, API adapters), not in prompts/planners/LLM routers.

## 3. Orchestration Pattern

Closest match: **other (request-dispatch MVC/service orchestration)**, not multi-agent orchestration.

Control flow is synchronous action dispatch:

```php
// public/index.php
$dic->get(ApplicationRunner::class)->run(
    $dic->get(ServerRequestCreatorInterface::class)->fromGlobals(),
    [ShowAction::REQUEST_KEY => ShowAction::class],
    ShowAction::REQUEST_KEY
);
```
`public/index.php:32-38`

```php
// ApplicationRunner::run
$action_name = htmlspecialchars($body['action'] ?? $request->getQueryParams()['action'] ?? '');
if (array_key_exists($action_name, $action_list) === false) { $action_name = $default_action; }
$handler = $this->dic->get($handler_name);
$response = $handler->run($request, $this->gatekeeperFactory->createGuiGatekeeper());
```
`src/Module/Application/ApplicationRunner.php:73-103`

There is also plugin-based workflow extension (still deterministic, not agentic): accepted “wanted” items trigger plugin processors in sequence (`src/Module/Wanted/WantedManager.php:104-115`).

## 4. Tools & External Integrations

This repo integrates many external services/tools, but they are classic API/plugin integrations rather than LLM tools.

- **MusicBrainz API** for missing artist/release data via `MusicBrainz\MusicBrainz` client (`src/Module/Wanted/MissingArtistFromMusicBrainzRetriever.php:35-95`, `src/Module/Wanted/WantedManager.php:45-63`).
- **Spotify Web API** for artwork lookup through `SpotifyWebAPI` session/search (`src/Module/Art/Collector/SpotifyCollectorModule.php:32-34`, `:80-110`, `:165-210`).
- **Seafile API** (Guzzle + Seafile SDK) for remote catalog traversal/download (`src/Module/Catalog/SeafileAdapter.php:29-33`, `:130-170`, `:326-352`).
- **Generic HTTP fetching/cURL** utility used across modules (`src/Module/Util/WebFetcher/WebFetcher.php:33-39`, `:65-84`, `:91-111`).
- **WebSocket server (Ratchet stack)** launched from CLI command for broadcast/echo routes (`src/Module/Cli/RunWebsocketCommand.php:79-85`; dependency in `composer.json:57-58`).
- **Plugin system** dynamically loads plugin modules by type and executes feature-specific hooks (`src/Module/System/Plugin/PluginRetriever.php:41-52`, `src/Module/Wanted/WantedManager.php:109-114`).
- **No RAG stack** (no vector store wiring, embedding pipeline, or retrieval-to-generation chain found in source/dependencies).

## 5. Notable Code Walkthrough

- `public/index.php:26-38` - Main web entrypoint; boots container from `Init.php` and delegates to `ApplicationRunner`, establishing the core request→action execution path.
- `src/Module/Application/ApplicationRunner.php:67-157` - Central dispatcher with action selection, DI handler resolution, gatekeeper wiring, and exception handling; this is the orchestration core for UI actions.
- `src/Module/Wanted/WantedManager.php:54-117` - Business workflow for wanted media: DB writes, optional auto-accept, MusicBrainz-assisted delete, and plugin hook invocation.
- `src/Module/Wanted/MissingArtistFromMusicBrainzRetriever.php:68-128` - External metadata retrieval component with caching/error handling; representative of external API enrichment patterns.
- `src/Module/Art/Collector/SpotifyCollectorModule.php:70-210` - Concrete third-party integration module showing credential handling, token refresh/retry logic, and search/result mapping for artwork collection.

## 6. Use-Case Mapping

The assigned label `RAG + Agents` appears incorrect for this repository. The codebase does not implement LLM generation, retrieval-augmented prompting, multi-agent coordination, or prompt graphs. Instead, it implements **workflow automation for media management/streaming operations**: request dispatch, metadata/art ingestion from external APIs, catalog synchronization, plugin-triggered processing, and operational CLI services (`src/Module/Application/ApplicationRunner.php`, `src/Module/Wanted/*`, `src/Module/Art/Collector/*`, `src/Module/Cli/RunWebsocketCommand.php`). A better category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Mature modular architecture with DI + action-handler separation (`src/Module/Application/ApplicationRunner.php`).
  - Broad real-world integration surface (MusicBrainz, Spotify, Seafile, WebSocket, plugin ecosystem).
  - Practical fault handling and retries in external I/O paths (e.g., Spotify token/429 handling, Seafile throttling).
  - Extensibility through plugin type retrieval and hook execution (`src/Module/System/Plugin/PluginRetriever.php`).
  - Large, domain-specific feature set for streaming/catalog workflows.

- **Limitations:**
  - No LLM, no agent abstractions, no prompt/planner/role runtime.
  - No RAG pipeline (no embeddings/vector index/retriever-generator loop).
  - “Agent” terminology can be misleading because it mostly means client user-agent telemetry fields.
  - Some integrations are legacy-style and tightly coupled to domain modules rather than unified integration interfaces.
  - Not suitable as evidence for contemporary autonomous AI orchestration benchmarks.

- **Research relevance:**
  - Good evidence of **non-LLM workflow orchestration** in a large production PHP system.
  - Useful for studying plugin-based extensibility and API integration reliability patterns.
  - Can be cited as a counterexample where “agent” labels in metadata do not imply AI agents.
  - Relevant to operational automation in media platforms, not multi-agent intelligence.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
