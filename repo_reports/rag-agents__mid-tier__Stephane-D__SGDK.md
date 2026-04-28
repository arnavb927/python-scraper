---
repo_name: Stephane-D/SGDK
url: "https://github.com/Stephane-D/SGDK"
stars: 2107
forks: 219
contributors_count: 58
last_commit_date: "2026-04-22T21:42:33+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 5
architecture_labels: [Custom/Other]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T14:14:28.043898+00:00"
model: auto
duration_s: 129.5
clone_size_kb: 234625
uses_mas: no
final_use_case: None
---
## 1. Overview

`Stephane-D/SGDK` is a Sega Mega Drive / Genesis development kit, not an AI-agent system. Users run SGDK’s build pipeline (`make`, CMake targets, `rescomp`, `xgmtool`, assembler/linker steps) to compile C/ASM game code and assets into a ROM binary (`out/.../rom.bin`) that can run on hardware or emulators (`makefile.gen:148-189`, `CMakeLists.txt:20-110`). The repository includes the runtime library (`src/*.c`, `src/*.s`), resource compiler tooling in Java (`tools/rescomp`), and format conversion utilities in C (`tools/xgmtool`, `tools/bintos`). The problem it solves is retro console software production: asset conversion, memory/layout handling, and ROM generation for the 68000/Z80 platform (`readme.md:6-9`, `readme.md:43`).

## 2. Agent Framework & Architecture

No LLM-agent framework is used. I found no runtime use of LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, OpenAI/Anthropic SDKs, prompt orchestration, or RAG/vector-store code in the source tree; the codebase is primarily C/ASM and Java build/tooling.

The actual architecture is a game SDK + compiler toolchain. At build time, `makefile.gen` orchestrates source compilation, resource compilation (`rescomp.jar`), Z80 assembly conversion (`sjasm` + `bintos`), and final ROM linking (`makefile.gen:229-243`, `makefile.gen:185-189`). At runtime, the SGDK library initializes VDP/video, memory, interrupts, audio, sprite systems, and optional cooperative multitasking for game loops (`src/vdp.c:64-130`, `src/sys.c:98-121`, `inc/task.h:7-19`).

The closest “agent-like” concept here is SGDK’s *task* subsystem (supervisor task + user task), but this is low-level CPU scheduling for game/network processing, not autonomous LLM agents (`inc/task.h:48-75`, `src/task.s:92-131`).

## 3. Orchestration Pattern

Closest match: **other** (deterministic build/resource processing pipeline, plus cooperative scheduler), not a multi-agent AI pattern.

Control flow is sequential and command-driven in `rescomp`: parse each resource line, resolve a processor by type, then execute it.

```799:832:tools/rescomp/src/sgdk/rescomp/Compiler.java
private static Resource execute(String input)
{
    ...
    final String type = fields[0];
    final Processor processor = getResourceProcessor(type);
    ...
    return processor.execute(fields);
}
```

```136:153:tools/rescomp/src/sgdk/rescomp/Compiler.java
for (String l : lines)
{
    ...
    final Resource resource = execute(line);
    ...
    else
        addResource(resource);
}
```

The runtime task scheduler is a cooperative context switch between supervisor/user tasks (again, not LLM agents):

```92:103:src/task.s
func TSK_superPend
        tst.l  task_pc
        beq.s  no_task
        move.w 6(%sp), task_lock
        bra.s  userYield

func TSK_userYield
```

## 4. Tools & External Integrations

- **Cross-compilation toolchain (m68k-elf GCC/AR/linker)**: wired in CMake and makefiles for ROM build (`CMakeLists.txt:5-16`, `makefile.gen:97-118`, `makefile.gen:185-189`).
- **Resource compiler (`rescomp.jar`, Java)**: converts `.res` declarations into assembly/header outputs (`CMakeLists.txt:44`, `makefile.gen:235-243`, `tools/rescomp/src/sgdk/rescomp/Launcher.java:36-74`).
- **Audio conversion tools (`xgmtool`)**: VGM/XGM/ZGM conversion and optimization for Mega Drive audio workflows (`tools/xgmtool/src/xgmtool.c:35-45`, `tools/xgmtool/src/xgmtool.c:149-206`).
- **Assembler/conversion helpers (`sjasm`, `bintos`)**: compiles Z80 sources and converts binaries to assembly form (`CMakeLists.txt:33-37`, `CMakeLists.txt:81-92`, `tools/bintos/src/bintos.c:159-199`).
- **Optional MegaWiFi networking**: HTTP/HTTPS/socket support for games via MegaWiFi module; includes URLConnection utilities in shared Java tools and C runtime APIs (`src/ext/mw/README.md:68-79`, `src/ext/mw/README.md:104-111`, `tools/commons/src/sgdk/tool/NetworkUtil.java:546-598`).
- **LLM/RAG integrations**: none found (no embeddings/vector DB/retrievers/model APIs).

## 5. Notable Code Walkthrough

- `makefile.gen:148-243` - Core ROM build graph: compile C/ASM/resources, run `rescomp`, assemble/link, export `rom.bin`; this is the operational entrypoint most users run.
- `tools/rescomp/src/sgdk/rescomp/Compiler.java:63-85,136-191,799-870` - Registers resource processors, parses `.res` scripts, dispatches processor plugins, and emits assembly/header/dependency outputs.
- `src/vdp.c:64-130,133-190` - Initializes Mega Drive VDP state, VRAM layout, palettes, and screen defaults; foundational runtime subsystem for graphics.
- `src/sprite_eng.c:120-153,160-220` - Sprite engine setup/reset and VRAM region management; critical for in-game entity rendering and memory behavior.
- `src/task.s:38-51,92-131,136-149` - Assembly-level cooperative task switching between supervisor and user contexts; enables background processing patterns used by MegaWiFi integrations.

## 6. Use-Case Mapping

The assigned label **“RAG + Agents” is incorrect** for this repository. SGDK does not implement retrieval-augmented generation, LLM prompting, agent planning, or multi-agent coordination at runtime. Its “task” APIs are CPU scheduling primitives for game loops and network polling (`inc/task.h:7-19`, `src/task.s:92-131`), and tooling is deterministic compilation/conversion (`tools/rescomp/...`, `tools/xgmtool/...`).

Better category: **None** (this is a retro game SDK/toolchain project rather than an AI-agent system in the provided taxonomy).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - End-to-end, production-grade toolchain from source/assets to final ROM (`makefile.gen:148-243`).
  - Clear modular build tooling (resource compiler, sound converter, symbol tools) with reproducible CLI workflows (`CMakeLists.txt:20-37`, `tools/rescomp/src/sgdk/rescomp/Launcher.java:36-53`).
  - Deep hardware-focused runtime abstractions (VDP, sprites, DMA, interrupts), useful for constrained-system engineering (`src/vdp.c:64-130`, `src/sprite_eng.c:120-220`).
  - Extensible resource compiler plugin model via jar-loaded `Processor` classes (`tools/rescomp/src/sgdk/rescomp/Compiler.java:425-493`).

- **Limitations:**
  - No LLM/agent implementation despite “task” terminology; unsuitable for agentic-AI comparative studies.
  - Large portions are low-level C/ASM, increasing onboarding cost for non-embedded developers.
  - Build flow depends on specialized external binaries/toolchain setup (cross-compiler, Java, SGDK-specific tools).
  - Some networking features are hardware/module-specific (MegaWiFi), limiting general portability (`src/ext/mw/README.md:68-79`).

- **Research relevance:**
  - Good evidence for deterministic compiler-pipeline orchestration in embedded game development.
  - Useful case for cooperative multitasking/context switching design in constrained runtimes (`src/task.s:92-149`).
  - Relevant to studies of extensible DSL-to-binary asset compilation (`tools/rescomp/src/sgdk/rescomp/Compiler.java:136-191`).
  - Not suitable evidence for multi-agent LLM systems, RAG orchestration, or agent tool-use frameworks.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
