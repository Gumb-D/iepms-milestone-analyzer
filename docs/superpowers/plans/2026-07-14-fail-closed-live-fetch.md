# Fail-Closed Live Fetch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make live IEPMS analysis fail closed, produce verifiable per-run manifests, and prevent agents from presenting stale, partial, or invented results.

**Architecture:** Preserve the existing calculation engine and place a small protective runner around it. The runner executes the legacy analyzer in quarantine, verifies current-run XLSX and CSV evidence, rejects known partial-failure markers, and publishes a report only after the run contract passes.

**Tech Stack:** Python 3 standard library, existing pandas/requests/openpyxl dependencies, `unittest`, and `unittest.mock`.

## Global Constraints

- `--fetch` is `LIVE_FETCH`; all six expected XLSX exports and converted CSV inputs must be fresh and non-empty.
- `--offline` is `OFFLINE_LOCAL`; local analysis is permitted but must not claim latest data.
- Invocation without exactly one execution mode is rejected.
- Failed runs write a failed manifest, return non-zero, publish no report, and do not update `output/latest.json`.
- Existing milestone mappings, project identifiers, DU identifiers, view identifiers, and SLA thresholds remain unchanged.
- Tests require no ZTE network access or credentials.

---

### Task 1: Run Contract and Freshness Verification

**Files:**
- Create: `scripts/run_contract.py`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_run_contract.py`

**Interfaces:**
- Produces: `RunContext`, `create_run_context`, `verify_fresh_files`, `verify_downloaded_files`, `write_manifest`, and `update_latest_pointer`.

- [x] Write failing tests for fresh/non-empty file verification, failed-manifest diagnostics, and atomic latest-pointer replacement.
- [x] Implement Malaysia-time run IDs and isolated `output/runs/<run_id>/` directories.
- [x] Implement extension-aware freshness verification.
- [x] Implement atomic JSON writes using a temporary sibling and `os.replace`.
- [x] Verify with `python -m unittest tests.test_run_contract -v`.

---

### Task 2: Protective Safe Runner

**Files:**
- Create: `scripts/iepms_safe_runner.py`
- Create: `tests/test_safe_runner.py`

**Interfaces:**
- Consumes: the existing `scripts/IEPMS_Milestone_Analyzer.py` as a subprocess.
- Produces: `parse_args(argv=None)`, `run(argv=None) -> int`, and `main()`.

- [x] Require exactly one of `--fetch` or `--offline`.
- [x] Execute the legacy analyzer in a quarantine output directory.
- [x] Capture exit code, stdout, and stderr.
- [x] Require `ANALYSIS COMPLETE!` and a non-empty quarantine report.
- [x] On failure, delete quarantine output, write a failed manifest, return `2`, and preserve the previous latest pointer.
- [x] On success, move report evidence into the run directory, write a success manifest, and atomically update `output/latest.json`.

---

### Task 3: Live Evidence and Partial-Result Guards

**Files:**
- Modify: `scripts/iepms_safe_runner.py`
- Modify: `scripts/run_contract.py`
- Modify: `tests/test_safe_runner.py`

**Interfaces:**
- Requires these six export names: `2023_TX_Rollout`, `2024_Celcomdigi_BAU`, `Jendela_TX_Migration`, `TX_Mini_Project`, `MW_EOS_Swap`, and `ZTE_TX_MINI`.

- [x] Require a fresh, non-empty XLSX for every expected export.
- [x] Require a fresh, non-empty CSV for every expected export because the calculation engine reads CSV.
- [x] Count an export as downloaded only when both current-run files pass.
- [x] Reject legacy analyzer markers for incomplete fetch, failed exports, XLSX conversion errors, per-file processing errors, and explicit server failures.
- [x] Add regression tests proving stale/missing CSV and partial processing errors cannot publish a report.

---

### Task 4: Agent Guardrails and Documentation

**Files:**
- Modify: `SKILL.md`
- Modify: `iepms_skill/SKILL.md`
- Modify: `README.md`
- Create: `docs/superpowers/specs/2026-07-14-fail-closed-live-fetch-design.md`

**Interfaces:**
- Consumers read `output/latest.json`, then the referenced manifest, then only the manifest-declared report.

- [x] Require the safe runner for live and offline reporting.
- [x] Prohibit fabrication, simulation, estimation, memory-based reuse, and silent fallback.
- [x] Require current run ID, year, mode, status, source, and file-set verification.
- [x] Keep both skill playbooks byte-identical.
- [x] Document live/offline commands, quarantine behavior, manifests, latest pointer, and XLSX/CSV freshness requirements.

---

### Task 5: Verification and Draft PR

**Files:**
- Verify all branch changes.

- [x] Run syntax checks:

```bash
python -m py_compile scripts/IEPMS_Milestone_Analyzer.py scripts/iepms_safe_runner.py scripts/run_contract.py
```

- [x] Run network-free tests:

```bash
python -m unittest discover -s tests -v
```

- [ ] Compare the branch to `main` and confirm the legacy calculation engine and business constants are unchanged.
- [ ] Open a Draft PR linked to Issue #1.
- [ ] Complete live ZTE VPN UAT before marking the PR ready for merge.
