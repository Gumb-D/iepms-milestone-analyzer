# Fail-Closed Live Fetch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make live IEPMS analysis fail closed, produce verifiable per-run manifests, and prevent agents from presenting stale or invented results.

**Architecture:** Add a small `run_contract.py` module responsible for execution modes, run directories, manifest writing, file-set verification, and atomic latest-pointer updates. Keep existing milestone/SLA calculations in `IEPMS_Milestone_Analyzer.py`, but route CLI orchestration through the run contract and stop before analysis when live fetch verification fails.

**Tech Stack:** Python 3 standard library, existing pandas/requests/openpyxl dependencies, `unittest`, `unittest.mock`.

## Global Constraints

- `--fetch` is `LIVE_FETCH`; all expected exports must be freshly downloaded in the current run.
- `--offline` is `OFFLINE_LOCAL`; local analysis is permitted but must not claim latest data.
- Invocation without exactly one execution mode is rejected.
- Failed live runs write a failed manifest, return non-zero, generate no report, and do not update `output/latest.json`.
- Existing milestone mappings and SLA thresholds must remain unchanged.
- Tests must not require ZTE network access or credentials.

---

### Task 1: Run Contract Module

**Files:**
- Create: `scripts/run_contract.py`
- Create: `tests/test_run_contract.py`

**Interfaces:**
- Produces: `RunContext`, `create_run_context(output_dir, target_year, mode, now=None)`, `verify_downloaded_files(input_dir, expected_files, run_started_epoch)`, `write_manifest(context, status, downloaded_files, missing_files, report_path=None, error=None)`, and `update_latest_pointer(output_dir, manifest_path)`.

- [ ] **Step 1: Write failing tests**

Test that live verification requires every expected non-empty `.xlsx` file to have an mtime at or after the run start, failed manifests retain diagnostic metadata, and latest-pointer replacement is atomic.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.test_run_contract -v`

Expected: import failure because `scripts.run_contract` does not exist.

- [ ] **Step 3: Implement the minimal run contract**

Use a frozen dataclass:

```python
@dataclass(frozen=True)
class RunContext:
    run_id: str
    mode: str
    target_year: int
    started_at: str
    started_epoch: float
    run_dir: str
    manifest_path: str
    report_path: str
```

`verify_downloaded_files` returns `(downloaded_files, missing_files)` using exact expected clean names converted to `<name>.xlsx`; zero-byte or pre-run files count as missing.

`write_manifest` writes JSON via a temporary sibling file and `os.replace`.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m unittest tests.test_run_contract -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add run manifest contract`

---

### Task 2: Explicit CLI Modes and Fail-Closed Fetch

**Files:**
- Modify: `scripts/IEPMS_Milestone_Analyzer.py`
- Create: `tests/test_analyzer_modes.py`

**Interfaces:**
- Consumes: Task 1 run-contract functions.
- Produces: `parse_args(argv=None)` and `run(argv=None) -> int`; `main()` calls `raise SystemExit(run())`.

- [ ] **Step 1: Write failing mode tests**

Cover:

```python
self.assertNotEqual(run([]), 0)
self.assertNotEqual(run(["--fetch", "--offline"]), 0)
```

Mock `execute_api_fetch_workflow` to return an incomplete downloaded set and assert:

- return code is non-zero;
- report path is absent;
- `latest.json` is absent or unchanged;
- failed manifest exists.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.test_analyzer_modes -v`

Expected: failures because the analyzer has no explicit offline mode and currently continues after failed fetch.

- [ ] **Step 3: Implement explicit execution modes**

Add mutually exclusive required arguments:

```python
mode_group = parser.add_mutually_exclusive_group(required=True)
mode_group.add_argument("--fetch", action="store_true")
mode_group.add_argument("--offline", action="store_true")
```

Refactor orchestration into `run(argv=None) -> int`. Create the run context before fetch. In live mode, call the fetch workflow, verify exact expected files, and on any failure write `FAILED` manifest and immediately return `2`. Do not call conversion or report generation on this path.

Change `execute_api_fetch_workflow` to return the clean names successfully downloaded rather than a boolean. Failed or timed-out names remain absent from that return set.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m unittest tests.test_analyzer_modes -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

Commit message: `fix: fail closed on incomplete live fetch`

---

### Task 3: Per-Run Report and Successful Manifest

**Files:**
- Modify: `scripts/IEPMS_Milestone_Analyzer.py`
- Modify: `tests/test_analyzer_modes.py`

**Interfaces:**
- Consumes: `RunContext.report_path`, `write_manifest`, and `update_latest_pointer`.
- Produces: successful manifests whose `report_path` references the report generated in the current run.

- [ ] **Step 1: Write failing success-path tests**

For offline mode with a temporary valid fixture, assert:

- return code is zero;
- report exists under `output/runs/<run_id>/`;
- manifest has `status=SUCCESS`, `mode=OFFLINE_LOCAL`, and source `LOCAL_INPUT`;
- `output/latest.json` points to that manifest.

For mocked live success, assert exact expected/downloaded set equality and source `ZTE_IEPMS_API`.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.test_analyzer_modes -v`

Expected: report still targets the legacy fixed path and no success manifest/latest pointer exists.

- [ ] **Step 3: Route successful output through the run context**

Set `output_report = context.report_path`. After report generation, write the success manifest, atomically update `output/latest.json`, and print run ID, mode, manifest path, and report path. Only then print `ANALYSIS COMPLETE`.

- [ ] **Step 4: Run full test suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

Commit message: `feat: publish verified per-run reports`

---

### Task 4: Agent Guardrails and Documentation

**Files:**
- Modify: `SKILL.md`
- Modify: `iepms_skill/SKILL.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `output/latest.json` and the referenced manifest contract.
- Produces: operational instructions that prohibit fallback and fabrication.

- [ ] **Step 1: Update both skills identically**

Require agents to:

1. execute with `--fetch` unless offline was explicitly requested;
2. require exit code zero;
3. read `output/latest.json` and its manifest;
4. verify current run ID, year, mode, success status, and exact expected/downloaded equality in live mode;
5. read only the manifest-declared report;
6. never fabricate, simulate, estimate, reconstruct, summarize from memory, or reuse an old report;
7. return only the factual failure message when verification fails.

- [ ] **Step 2: Update README commands**

Document:

```bash
python scripts/IEPMS_Milestone_Analyzer.py --fetch --year 2026
python scripts/IEPMS_Milestone_Analyzer.py --offline --year 2026
```

Explain run directories, manifests, and the difference between latest live data and explicitly local data.

- [ ] **Step 3: Verify skill parity**

Run a script or comparison that confirms `SKILL.md` and `iepms_skill/SKILL.md` are byte-identical.

- [ ] **Step 4: Run full tests**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

Commit message: `docs: enforce verified report consumption`

---

### Task 5: Final Verification and Draft PR

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run syntax checks**

Run: `python -m py_compile scripts/IEPMS_Milestone_Analyzer.py scripts/run_contract.py`

Expected: exit code 0.

- [ ] **Step 2: Run all tests**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass with no network access.

- [ ] **Step 3: Review diff for scope**

Confirm no milestone mapping, SLA threshold, project ID, DU model ID, or view ID was unintentionally changed.

- [ ] **Step 4: Open a Draft PR**

Title: `Fail closed on incomplete IEPMS live fetch`

Body must link Issue #1, summarize behavior changes, include verification commands/results, and flag live ZTE VPN UAT as the remaining human checkpoint.