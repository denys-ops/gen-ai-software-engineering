# Homework 4 — 4-Agent Bug-Fix Pipeline: Jedi Holocron Vault

**Author:** Denys Kondratiuk
**Course:** GenAI and Agentic AI for Software Engineering

---

## Overview

A fully automated 6-agent pipeline that researches, verifies, plans, fixes, security-scans, and
unit-tests bugs in a small FastAPI application — all triggered by a single command.

The sample app is the **Jedi Holocron Vault**: a filesystem-backed REST API with three seeded
defects. The pipeline finds them, fixes them, and proves the fixes with generated unit tests.

---

## The Application

`POST /holocron` — store a holocron `{name, body}`  
`GET  /holocron/{name}` — retrieve a holocron by name

Three seeded defects in the *before* state:

| ID | Type | Description |
|----|------|-------------|
| `001` | CRITICAL security | Write path traversal — `../evil.txt` escapes the vault |
| `002` | HIGH bug | Missing holocron returns 500 instead of 404 |
| `003` | MEDIUM bug | Duplicate POST silently overwrites instead of returning 409 |

---

## The Pipeline

```
bug-researcher → research-verifier → bug-planner → bug-fixer → security-verifier → unit-test-generator
```

Single command: `./run-pipeline.sh [bug-id]`

### Agent model selection

| Agent | Model | Rationale |
|-------|-------|-----------|
| `bug-researcher` | haiku | Mechanical extraction of file:line anchors from source and bug context |
| `research-verifier` | opus | Quality gate — careful fact-checking against source, applies 4-tier rubric |
| `bug-planner` | sonnet | Synthesis — turns verified research into a concrete before/after implementation plan |
| `bug-fixer` | haiku | Mechanical — applies an explicit before/after plan and runs tests |
| `security-verifier` | opus | Quality gate — security reasoning over changed code, rates CRITICAL→INFO |
| `unit-test-generator` | haiku | Scaffolding — generates FIRST-compliant pytest tests from a fixed template |

Opus is used only at the two verification gates where careful reasoning matters; haiku handles
the three mechanical stages; sonnet handles the one synthesis step. This reduces cost while
keeping quality high at the gates that matter.

### Skills

| Skill | Used by | Purpose |
|-------|---------|---------|
| `research-quality-measurement` | research-verifier | 4-tier rubric (EXCELLENT/GOOD/FAIR/POOR) for rating research quality |
| `unit-tests-FIRST` | unit-test-generator | FIRST principles (Fast/Independent/Repeatable/Self-validating/Timely) for test generation |

### Gate checks

The runner checks each agent's output file after it writes it. If a file starts with `BLOCKED:`
or its `Overall Status` line is `FAILED`, the remaining stages for that bug are skipped.
The pipeline continues to the next bug and exits non-zero when done.

---

## Pipeline Outputs (after run)

For each `bug-id` under `context/bugs/<bug-id>/`:

| File | Written by |
|------|-----------|
| `research/codebase-research.md` | bug-researcher |
| `research/verified-research.md` | research-verifier |
| `implementation-plan.md` | bug-planner |
| `fix-summary.md` | bug-fixer |
| `security-report.md` | security-verifier |
| `test-report.md` | unit-test-generator |

Generated tests land in `tests/test_<bug_id>.py`.

---

## Results

All three bugs were successfully fixed and verified by the pipeline:

| Bug | Research | Fix | Tests |
|-----|----------|-----|-------|
| `001-security-path-traversal` | EXCELLENT | PASSED | PASS |
| `002-missing-404` | EXCELLENT | PASSED | PASS |
| `003-silent-overwrite` | EXCELLENT | PASSED | PASS |

---

## AI Tools Used

- **Claude Code (claude-opus-4-7)** — entire pipeline design, agent prompts, skill definitions,
  runner script, and debugging of gate-check logic
- **Claude headless CLI (`claude -p`)** — drives all 6 agents non-interactively per bug
- Model selection rationale was deliberately cost-conscious: opus only at the two reasoning gates

## Screenshots

See `docs/screenshots/`:

| Folder / File | Content |
|---------------|---------|
| `1-run-pipeline/` | Full pipeline terminal output (all 6 stages, all 3 bugs) |
| `2-fixes-applied/` | Fixed `main.py` and `storage.py` after pipeline run |
| `3-security-report/` | Security report summaries for each bug |
| `4-unit-tests.png` | Pytest output — all generated tests passing |
