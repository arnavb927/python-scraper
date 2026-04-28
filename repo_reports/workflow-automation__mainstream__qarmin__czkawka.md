---
repo_name: qarmin/czkawka
url: "https://github.com/qarmin/czkawka"
stars: 30678
forks: 1029
contributors_count: 88
last_commit_date: "2026-04-21T17:51:43+00:00"
primary_use_case: Workflow Automation
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T10:31:37.309848+00:00"
model: auto
duration_s: 59.6
clone_size_kb: 14709
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`qarmin/czkawka` is a Rust workspace for cleaning and analyzing filesystem clutter (duplicates, empty files/folders, similar images/videos, bad extensions, broken files, etc.) via multiple frontends: CLI (`czkawka_cli`), desktop GUIs (`krokiet`, `czkawka_gui`), and Android (`cedinia`). A user runs one of these frontends (e.g., `czkawka_cli` command or GUI app), points it at directories, and gets scan results plus optional cleanup actions (delete/move/trash/fix/export). The core logic lives in `czkawka_core` and is reused across frontends. This is primarily a high-performance file maintenance tool, not an LLM product.

## 2. Agent Framework & Architecture

No multi-agent LLM framework is used in runtime product paths. I found no LangGraph/LangChain/AutoGen/CrewAI/LlamaIndex imports, and no planner/router/multi-role agent abstractions in the Rust applications.

The only LLM-related code is an auxiliary Python translation script under `misc/ai_translate/translate.py`, which calls a local Ollama model with a single `ollama.chat(...)` prompt per phrase. This is a one-shot translation helper for localization maintenance, not an orchestrated agent system (`misc/ai_translate/translate.py:55-77`, `misc/pyproject.toml:5-12`, `justfile:256-270`).

Architecture-wise, the product is a modular Rust toolchain: frontends register UI/CLI handlers, dispatch to `czkawka_core` scanners, and stream progress/results. Intelligence is algorithmic (hashing, traversal, matching), not prompt- or agent-driven.

## 3. Orchestration Pattern

Closest match: **other (event-driven + command dispatch), not multi-agent**.

Control flow is command/callback orchestration of deterministic scanning modules. In CLI, subcommands are matched and routed to tool functions; each function configures a scanner and runs `tool.search(...)` (`czkawka_cli/src/main.rs:73-90`, `:118-153`).

```75:82:czkawka_cli/src/main.rs
.spawn(move || match command {
    Commands::Duplicates(duplicates_args) => duplicates(duplicates_args, &stop_flag, &progress_sender),
    Commands::EmptyFolders(empty_folders_args) => empty_folders(empty_folders_args, &stop_flag, &progress_sender),
    Commands::BiggestFiles(biggest_files_args) => biggest_files(biggest_files_args, &stop_flag, &progress_sender),
    Commands::EmptyFiles(empty_files_args) => empty_files(empty_files_args, &stop_flag, &progress_sender),
    Commands::Temporary(temporary_args) => temporary(temporary_args, &stop_flag, &progress_sender),
```

The GUI frontend (`krokiet`) is similarly event-driven: it wires button/callback handlers to scanning and file-action connectors, with shared state and progress channels (`krokiet/src/main.rs:142-169`).

```142:149:krokiet/src/main.rs
connect_delete_button(&app, progress_sender.clone(), stop_flag.clone());
connect_trash_button(&app, progress_sender.clone(), stop_flag.clone());
connect_scan_button(&app, progress_sender.clone(), stop_flag.clone(), Arc::clone(&shared_models), Arc::clone(&audio_player));
connect_stop_button(&app, stop_flag.clone());
connect_open_items(&app);
connect_progress_gathering(&app, progress_receiver);
connect_add_remove_directories(&app);
connect_show_preview(&app, Arc::clone(&shared_models));
```

## 4. Tools & External Integrations

- **Filesystem scanning and mutation (core product):** recursive traversal, duplicate detection, cleanup actions, result export; wired through `czkawka_core` tools and frontend dispatch (`czkawka_cli/src/main.rs:17-33`, `:640-661`).
- **CLI + GUI frontends:** `clap` command parsing and Slint/GTK UI callback wiring (`czkawka_cli/src/main.rs:6-8`, `krokiet/src/main.rs:27`, `czkawka_gui/src/main.rs`).
- **Progress/event channels:** `crossbeam_channel` and threads for async scanning updates (`czkawka_cli/src/main.rs:69-75`, `krokiet/src/main.rs:123-147`).
- **FFmpeg tooling (non-LLM):** video optimization/probing and hardware encoder checks (`krokiet/src/main.rs:14`, `:223-253`; `czkawka_cli/src/main.rs:30-33`).
- **Local LLM (maintenance script only):** Ollama chat API used for translation generation in `misc/ai_translate/translate.py:55-77`; dependency/config in `misc/pyproject.toml:5-12` and `justfile:258-270`.
- **No MCP/vector DB/web-search/browser-agent stack:** none found in codebase search.

## 5. Notable Code Walkthrough

- `czkawka_cli/src/main.rs:52-116` - CLI entrypoint: parses subcommands, sets logger/cache, spawns scanning worker thread, handles Ctrl+C, prints outputs and exit codes.
- `czkawka_cli/src/main.rs:118-662` - Representative tool execution pattern: build typed parameters, configure shared options, run `search`, optionally `fix_items`, then serialize results.
- `krokiet/src/main.rs:88-185` - Main desktop app bootstrap: initialize settings/UI models, register all scan/file-action callbacks, then run Slint event loop.
- `misc/ai_translate/translate.py:55-87` - Single-call LLM translation helper via `ollama.chat`; no planner/worker roles, memory graph, or agent routing.
- `justfile:256-277` - Translation automation tasks (`prepare_translations_deps`, `translate`, `validate_translations`) showing LLM usage is offline localization support, not runtime app behavior.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** is directionally reasonable for the CLI/tooling aspect: users automate disk hygiene workflows (scan, detect, export/fix/delete) via commands and scripts. However, this repository does **not** realize workflow automation through LLM agents; it does so through deterministic Rust modules and command/callback orchestration.

Given the allowed categories, `Workflow Automation` remains the best fit for the repo’s practical usage, but with `USES_MAS = no` because there is no coordinated multi-agent runtime.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - High-performance, production-grade automation for file cleanup with broad tool coverage across CLI/GUI/mobile.
  - Clear modular architecture (`czkawka_core` reused by multiple frontends) with strong separation of concerns.
  - Event-driven concurrency and progress reporting are explicit and robust.
  - Practical “fix” paths (rename, exif cleanup, video optimize, delete/move/trash) beyond mere detection.
  - Includes reproducible maintenance workflows (`justfile`) and translation quality checks.

- **Limitations:**
  - No multi-agent or even single-agent runtime architecture; unsuitable as evidence of agent collaboration.
  - LLM usage is narrow and offline (translation helper script), not integrated into user-facing scanning flows.
  - No prompt management, planning, tool-selection policy, or agent memory mechanisms.
  - No agent observability/evaluation artifacts (trajectory logs, reward signals, benchmarks for agent behavior).
  - “Workflow automation” here is systems automation, not AI-agent automation.

- **Research relevance:**
  - Useful negative/control example in MAS studies: popular automation software without agentic AI.
  - Evidence of mature non-LLM orchestration patterns (event-driven callbacks + command dispatch) that MAS systems often replace.
  - Shows a bounded, low-risk niche use of local LLMs (translation assistance) in a larger non-agent codebase.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
