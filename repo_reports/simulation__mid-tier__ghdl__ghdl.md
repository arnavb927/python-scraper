---
repo_name: ghdl/ghdl
url: "https://github.com/ghdl/ghdl"
stars: 2799
forks: 411
contributors_count: 129
last_commit_date: "2026-04-22T05:36:28+00:00"
primary_use_case: Simulation
user_tier: Mid-Tier
total_score: 4
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Simulation]
generated_at: "2026-04-27T15:01:06.717315+00:00"
model: auto
duration_s: 106.1
clone_size_kb: 66787
uses_mas: no
final_use_case: Simulation
---
## 1. Overview

`ghdl/ghdl` is a VHDL compiler/simulator toolchain, not an LLM-agent application. Users run the `ghdl` CLI to analyze VHDL files (`-a`), elaborate designs (`-e`), and execute simulations (`-r` or `--elab-run`), producing compiled design artifacts and simulation results/waveforms. Internally, the project includes multiple backends (GCC/LLVM/JIT/mcode paths) and a Python binding (`pyGHDL`) plus a VHDL language server. The core problem it solves is deterministic hardware language compilation/elaboration/simulation and related developer workflows (linting, diagnostics, dependency management, test automation).

## 2. Agent Framework & Architecture

No LLM framework is used. I found no LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex/OpenAI/Anthropic runtime code in `src`/`pyGHDL` (keyword scan plus direct file inspection). The architecture is custom compiler/simulator infrastructure in Ada, with Python wrappers/tools around `libghdl`.

High-level flow is command-driven: backend entrypoints register command sets, then dispatch into a command executor. For example, `src/ghdldrv/ghdl_gcc.adb:27-44` wires command modules and then calls `Ghdlmain.Main`, while `src/ghdldrv/ghdlmain.adb:590-707` parses CLI args, resolves command handlers, decodes options, and executes actions.

“Intelligence” here is compiler semantics/elaboration logic, not prompts/planners: analysis and elaboration are implemented through VHDL AST/semantic routines and dependency handling (e.g., `src/ghdldrv/ghdlcomp.adb:265-311`, `src/ghdldrv/ghdldrv.adb:1702-1867`). The Python LSP server (`pyGHDL/lsp/vhdl_ls.py`, `pyGHDL/lsp/workspace.py`) provides editor diagnostics/navigation by invoking `libghdl` APIs, not by using language models.

## 3. Orchestration Pattern

Closest match: **sequential command pipeline** (custom CLI orchestration), not multi-agent.

Control flow is explicit and linear: register commands -> parse argv -> run selected command handler. Example:

```27:44:src/ghdldrv/ghdl_gcc.adb
procedure Ghdl_Gcc is
begin
   Ghdldrv.Backend := Ghdldrv.Backend_Gcc;
   Ghdldrv.Register_Commands;
   ...
   Ghdlmain.Register_Commands;
   Ghdlmain.Main;
end Ghdl_Gcc;
```

Within command handlers, operations run in fixed stages (analyze/elaborate/link/run). Example:

```1341:1361:src/ghdldrv/ghdldrv.adb
procedure Perform_Action (Cmd : in out Command_Elab_Run; ...)
begin
   Set_Elab_Units (Cmd, "--elab-run", Args, Run_Arg);
   Setup_Compiler (Cmd, False);
   Bind (Cmd);
   ...
   Link (Cmd, Add_Std => True, Disp_Only => False);
   Run_Design (Cmd, Cmd.Output_File, Args (Run_Arg .. Args'Last));
end Perform_Action;
```

This is orchestration of compiler stages/tools, not manager-worker or graph/swarm agents.

## 4. Tools & External Integrations

- **System toolchain invocation (compiler/assembler/linker, subprocess spawning):** wired in `src/ghdldrv/ghdldrv.adb:129-164`, `:538-573`, `:1097-1173`.
- **Filesystem and library-path management:** `src/ghdldrv/ghdldrv.adb:339-420`, `src/ghdldrv/ghdlmain.adb:519-588`.
- **Python bindings to native `libghdl` for analysis/LSP:** `pyGHDL/lsp/workspace.py:5-17`, `:46-69`, `:334-352`.
- **Language Server Protocol integration (editor RPC):** `pyGHDL/lsp/vhdl_ls.py:14-35`, `:95-140`.
- **Shell-based regression automation (testsuite orchestration):** `testsuite/testsuite.sh:118-175`, helper functions in `testsuite/testenv.sh:40-174`.
- **No LLM APIs, MCP servers, vector DBs, browser automation, or RAG pipeline** observed.

## 5. Notable Code Walkthrough

- `src/ghdldrv/ghdlmain.adb:58-81, 398-460, 590-707` - Core command dispatcher: registers commands, parses CLI options/response files, resolves command handlers, executes actions, and sets process exit status.
- `src/ghdldrv/ghdldrv.adb:167-330, 914-963, 1206-1361, 1673-1871` - Main GCC/LLVM-style driver logic implementing compile/analyze/elaborate/run/make pipelines, including external tool invocations and dependency-based rebuild decisions.
- `src/ghdldrv/ghdlcomp.adb:148-178, 265-311, 351-406, 584-628` - mcode/JIT-style compile/elaboration path: parses/analyzes VHDL units, configures top-level elaboration, and handles run semantics/errors.
- `pyGHDL/lsp/workspace.py:37-69, 169-231, 334-368, 392-423` - LSP workspace state and diagnostics engine: reads project config, parses documents with `libghdl`, gathers/publishes diagnostics, and powers hover/goto navigation.
- `testsuite/testenv.sh:40-108, 110-174, 247-262` - Reusable shell functions for analyze/elaborate/simulate/synthesis/cleanup, used by many regression suites to automate workflow validation.

## 6. Use-Case Mapping

The assigned primary use case **Simulation** is correct. The central runtime behavior is VHDL compilation + elaboration + simulation execution via commands like `-a`, `-e`, `-r`, and `--elab-run` (`src/ghdldrv/ghdldrv.adb:923-963`, `:1206-1312`, `:1341-1361`; `src/ghdldrv/ghdlcomp.adb:112-178`, `:685-708`).  

While the repo also includes significant workflow automation (testsuite scripts and CI-friendly harness), that is supporting infrastructure around the simulator rather than the primary product behavior.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Mature, explicit command orchestration with clear stage boundaries (analyze/elaborate/link/run) in Ada driver code.
  - Strong dependency-aware recompilation logic for large hardware projects (`make` path in `ghdldrv.adb`).
  - Rich ecosystem support: CLI, Python bindings, and LSP diagnostics/navigation over the same core compiler.
  - Extensive automated regression harness in shell testsuites spanning multiple domains (VPI/VHPI/synth/VESTS).

- **Limitations:**
  - No LLM or multi-agent runtime; not useful as evidence of agent coordination techniques.
  - Architecture is large/monolithic in places (very long command driver units), which raises onboarding complexity.
  - Heavy dependence on native toolchain/backend environment for some flows, increasing setup friction.
  - Some scripting utilities are shell-centric, which can reduce portability/ergonomics for non-Unix environments.

- **Research relevance:**
  - Strong example of deterministic, non-ML orchestration in compiler/simulator pipelines.
  - Useful baseline to contrast against agentic systems (rule-based command dispatch vs adaptive planning).
  - Evidence for robust workflow automation in traditional EDA tooling (regression/test harness orchestration).
  - Relevant for studies on language-server diagnostics architecture over compiler internals, not MAS/LLM behavior.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Simulation
