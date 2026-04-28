---
repo_name: erev0s/VAmPI
url: "https://github.com/erev0s/VAmPI"
stars: 1205
forks: 529
contributors_count: 8
last_commit_date: "2026-04-07T20:02:39+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 4
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T15:26:32.616013+00:00"
model: auto
duration_s: 48.0
clone_size_kb: 117
uses_mas: no
final_use_case: None
---
## 1. Overview

`VAmPI` is a deliberately vulnerable REST API built with Flask/Connexion to help users practice API security testing against OWASP-style flaws. A user runs the Python app (or Docker setup), initializes a demo SQLite database, and then interacts with endpoints for users/books plus JWT auth workflows. The implementation intentionally toggles insecure behaviors via a `vulnerable` flag, so the same endpoints can exhibit insecure or safer variants. In practice, this is a security training/test target, not an AI automation runtime.

## 2. Agent Framework & Architecture

No LLM or agent framework is used in the codebase. There are no imports or runtime hooks for LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, OpenAI SDKs, or equivalent in application modules/dependencies (`requirements.txt:1-9`, `app.py:1-17`, `config.py:1-28`).

Architecture is a classic API server pattern: `app.py` boots a Connexion/Flask app, `config.py` wires SQLAlchemy and OpenAPI routing, and endpoint handlers live in `api_views/*.py`. Business logic sits in handler functions and model methods (`models/user_model.py`, `models/books_model.py`), with vulnerability toggles embedded in branch logic (e.g., SQL injection path, authorization bypass path). The “intelligence” is static conditional code paths, not prompts/planners/agent coordination.

## 3. Orchestration Pattern

Closest match: **other** (single-process request/response web API), not a multi-agent orchestration pattern.

Control flow is OpenAPI operation routing -> handler function -> model/DB operations. Example routing definition in the OpenAPI spec:

```22:45:openapi_specs/openapi3.yml
operationId: api_views.main.populate_db
...
operationId: api_views.main.basic
```

And corresponding app wiring:

```7:27:config.py
vuln_app = connexion.App(__name__, specification_dir='./openapi_specs')
...
vuln_app.add_api('openapi3.yml')
```

Endpoint handlers then call validators/models directly (no agent handoff), e.g. token validation then DB query in `api_views/books.py:17-72` and `api_views/users.py:117-223`.

## 4. Tools & External Integrations

This project has **no agent tools/integrations** (no MCP, browser automation, shell tools, vector DBs, external LLM APIs).

What it does integrate:
- **HTTP API routing via OpenAPI/Connexion**: operation IDs map endpoints to Python functions (`config.py:7-27`, `openapi_specs/openapi3.yml:15-651`).
- **SQLite via SQLAlchemy**: local DB persistence for users/books (`config.py:9-15`, `models/user_model.py:11-102`, `models/books_model.py:6-29`).
- **JWT auth (PyJWT)**: token encode/decode and request auth checks (`models/user_model.py:30-53`, `api_views/users.py:117-129`).
- **JSON schema validation**: request payload checks (`api_views/users.py:57-60`, `api_views/books.py:18-22`).

## 5. Notable Code Walkthrough

- `config.py:7-27` — Core app composition: creates Connexion app, configures SQLAlchemy, registers custom error handler, and loads `openapi3.yml`; this is the central runtime bootstrap.
- `openapi_specs/openapi3.yml:15-651` — Declares all API routes and binds each to a Python `operationId`, defining overall control flow and auth requirements.
- `api_views/users.py:52-223` — Main user/account/auth endpoint logic, including registration/login/JWT checks and vulnerability-conditioned branches (e.g., enumeration, regex DoS path, weak authorization path).
- `api_views/books.py:17-72` — Book creation/read logic with JWT validation and an intentionally vulnerable object-level authorization branch.
- `models/user_model.py:30-81` — JWT encode/decode and user retrieval; includes deliberately unsafe SQL-string construction when vulnerability mode is enabled.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** does **not** match the actual repository behavior. The code implements a vulnerable API testbed for security education/assessment, not an AI-driven workflow engine or agent pipeline.  
Given the allowed categories, the best fit is **None** (it is not MAS, not code generation, not RAG, not browser/terminal agent use, and not simulation).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clean, inspectable vulnerable-vs-non-vulnerable branching for multiple API security failure modes (`api_views/users.py`, `api_views/books.py`, `models/user_model.py`).
  - OpenAPI-first routing makes endpoint behavior easy to enumerate and test (`openapi_specs/openapi3.yml`).
  - Minimal stack lowers setup friction for labs (Flask + SQLite + JWT).
  - Includes auth, CRUD, and data ownership flows that mirror common real API patterns.

- **Limitations:**
  - No LLM components, no agents, no multi-agent coordination runtime.
  - Limited architecture complexity (single service, local DB) reduces representativeness for modern distributed systems.
  - Security flaws are hand-coded toggles, not generated/adaptive attack surfaces.
  - Sparse test/benchmark harness for systematic comparative evaluation in-repo.

- **Research relevance:**
  - Useful as a baseline dataset/system for **API vulnerability detection** studies, not agentic-AI studies.
  - Can support reproducible experiments on static/dynamic security scanners against known vulnerable endpoints.
  - Illustrates pedagogical design pattern: controlled insecure branches under a runtime flag.
  - Not valid evidence for multi-agent orchestration, planning, or tool-using LLM systems.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
