# Final Acceptance Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-command fail-closed runner that performs guarded live fetch, validates six-file output, checks report/mapping consistency, compares against the successful offline baseline, and writes one final acceptance summary.

**Architecture:** A focused Python module will expose pure report-parsing and validation functions plus a thin orchestration layer around the existing `iepms_guarded_runner.py`. The existing guarded runner remains responsible for fresh export verification and report generation; the new runner adds baseline capture, structural/arithmetic checks, mapping identity checks, delta reporting, and a compact handoff.

**Tech Stack:** Python 3 standard library, `unittest`, existing IEPMS guarded runner and run manifest JSON.

## Global Constraints

- Default target year is `2026`.
- Require all six expected exports.
- Preserve existing local authentication and configuration.
- Fail closed with exit code `2`.
- Do not update PR state, mark Ready, or merge.
- Add no third-party dependencies.
- Use test-first RED/GREEN commits.

---

### Task 1: Report parser and consistency validator

**Files:**
- Create: `tests/test_final_acceptance_runner.py`
- Create: `scripts/final_acceptance_runner.py`

**Interfaces:**
- Produces: `parse_report(text: str) -> dict`
- Produces: `validate_report(parsed: dict, expected_models: list[str]) -> list[str]`
- Produces: `compare_reports(baseline: dict, live: dict) -> dict`

- [ ] **Step 1: Write failing parser and validation tests**

Create tests covering:

```python
from scripts.final_acceptance_runner import compare_reports, parse_report, validate_report


def test_parses_combined_du_and_sla_tables():
    parsed = parse_report(SAMPLE_REPORT)
    assert parsed["combined"]["RFS"]["total"] == 3
    assert parsed["models"]["TX Mini Project"]["RFS"]["total"] == 2
    assert parsed["sla"]["TI_L1"]["Combined"]["open"] == 3


def test_validation_rejects_combined_total_not_equal_to_models():
    parsed = parse_report(SAMPLE_REPORT)
    parsed["combined"]["RFS"]["total"] = 4
    errors = validate_report(parsed, EXPECTED_MODELS)
    assert any("combined RFS" in error for error in errors)


def test_compare_reports_returns_tx_mini_deltas():
    delta = compare_reports(parse_report(BASELINE_REPORT), parse_report(LIVE_REPORT))
    assert delta["models"]["TX Mini Project"]["RFS"] == 1
```

Use a complete in-test Markdown fixture containing eight milestone rows, six DU model sections, and three SLA tables.

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```bash
python -m unittest tests.test_final_acceptance_runner -v
```

Expected: import failure because `scripts.final_acceptance_runner` does not exist.

- [ ] **Step 3: Implement minimal parser and validator**

Create `scripts/final_acceptance_runner.py` with:

```python
MILESTONES = ("SOW", "TSS", "MC", "MOS", "TI", "L1", "RFS", "PAC")
SLA_KEYS = ("MC_MOS", "TI_L1", "MC_PAC")
EXPECTED_MODELS = (
    "2023 TX Rollout",
    "2024 Celcomdigi BAU",
    "Jendela TX Migration",
    "TX Mini Project",
    "MW EOS Swap",
    "ZTE TX MINI",
)


def parse_report(text: str) -> dict:
    """Return combined, models, and SLA tables parsed from analyzer Markdown."""


def validate_report(parsed: dict, expected_models=EXPECTED_MODELS) -> list[str]:
    """Return deterministic structure and arithmetic validation errors."""


def compare_reports(baseline: dict, live: dict) -> dict:
    """Return live-minus-baseline totals for combined, models, and SLA rows."""
```

The parser must read pipe tables, normalize bold milestone labels, verify twelve monthly values plus total, and associate each table with the current DU or SLA section.

- [ ] **Step 4: Run parser tests and verify GREEN**

Run:

```bash
python -m unittest tests.test_final_acceptance_runner -v
```

Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add scripts/final_acceptance_runner.py tests/test_final_acceptance_runner.py
git commit -m "feat: validate final acceptance reports"
```

---

### Task 2: Mapping identity checks and summary renderer

**Files:**
- Modify: `tests/test_final_acceptance_runner.py`
- Modify: `scripts/final_acceptance_runner.py`

**Interfaces:**
- Produces: `validate_mapping_document(text: str) -> list[str]`
- Produces: `render_summary(...) -> str`

- [ ] **Step 1: Write failing identity and summary tests**

Add tests:

```python
from scripts.final_acceptance_runner import render_summary, validate_mapping_document


def test_mapping_validation_requires_exact_tx_mini_identities():
    errors = validate_mapping_document(VALID_MAPPING_DOCUMENT)
    assert errors == []
    errors = validate_mapping_document(VALID_MAPPING_DOCUMENT.replace("Site Integrated", "Cut-over End Date"))
    assert any("ZTE TX MINI RFS" in error for error in errors)


def test_summary_contains_paths_status_and_key_deltas():
    text = render_summary(
        status="PASS",
        baseline_manifest="baseline/manifest.json",
        live_manifest="live/manifest.json",
        live_report="live/report.md",
        mapping_document="live/milestone_mappings.md",
        deltas=DELTA_FIXTURE,
        errors=[],
    )
    assert "# Final Acceptance Summary - PASS" in text
    assert "TX Mini Project" in text
    assert "ZTE TX MINI" in text
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python -m unittest tests.test_final_acceptance_runner -v
```

Expected: missing `validate_mapping_document` and `render_summary`.

- [ ] **Step 3: Implement exact identity checks and deterministic Markdown output**

Required mapping identities:

```python
REQUIRED_MAPPING_IDENTITIES = {
    ("TX Mini Project", "RFS"): ("Software Commissioning", "TX Integrated"),
    ("ZTE TX MINI", "RFS"): ("Software Commissioning", "Site Integrated"),
    ("ZTE TX MINI", "L1"): ("Q&EHS", "L1 Approved"),
    ("ZTE TX MINI", "TSS"): ("Survey&Design", "Physical Survey"),
}
```

`render_summary()` must include:

- PASS/FAIL status;
- baseline/live manifest paths;
- live report and mapping paths;
- automated check results;
- combined milestone deltas;
- TX Mini Project and ZTE TX MINI milestone deltas;
- three SLA combined deltas;
- errors when status is FAIL.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
python -m unittest tests.test_final_acceptance_runner -v
```

Expected: all Task 1 and Task 2 tests pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add scripts/final_acceptance_runner.py tests/test_final_acceptance_runner.py
git commit -m "feat: summarize final acceptance evidence"
```

---

### Task 3: One-command live orchestration

**Files:**
- Modify: `tests/test_final_acceptance_runner.py`
- Modify: `scripts/final_acceptance_runner.py`

**Interfaces:**
- Produces: `run(argv: list[str] | None = None) -> int`
- Produces CLI: `python -u scripts/final_acceptance_runner.py`

- [ ] **Step 1: Write failing orchestration tests**

Use temporary directories and patched subprocess execution to test:

```python

def test_run_executes_guarded_live_fetch_and_writes_pass_summary():
    # Seed a successful OFFLINE_LOCAL latest manifest/report.
    # Patch subprocess.run to create a successful LIVE_FETCH manifest/report/mapping.
    # Assert --fetch and --force-convert are passed, exit code is 0, and both summary copies exist.


def test_run_fails_closed_when_baseline_is_not_successful_offline():
    # Seed latest manifest with LIVE_FETCH or FAILED.
    # Assert exit code 2 and subprocess is not called.


def test_run_fails_when_guarded_live_output_lacks_mapping_complete_marker():
    # Return guarded runner code 0 but omit MAPPING_VALIDATION_COMPLETE.
    # Assert exit code 2.
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python -m unittest tests.test_final_acceptance_runner -v
```

Expected: missing `run()` orchestration behavior.

- [ ] **Step 3: Implement the orchestration**

`run()` must:

1. Parse `--year`, `--input-dir`, `--output-dir`, `--fetch-timeout-seconds`, and `--poll-interval-seconds`.
2. Capture and validate the baseline manifest before invoking live fetch.
3. Execute:

```python
[
    sys.executable,
    os.path.join(script_dir, "iepms_guarded_runner.py"),
    "--fetch",
    "--year", str(year),
    "--force-convert",
    "--input-dir", input_dir,
    "--output-dir", output_dir,
    "--fetch-timeout-seconds", str(fetch_timeout_seconds),
    "--poll-interval-seconds", str(poll_interval_seconds),
]
```

4. Stream combined stdout/stderr to the terminal while retaining it.
5. Require return code `0` and the three completion markers.
6. Read the new latest manifest and require a different manifest path from baseline.
7. Validate manifest mode/status/year/files/report.
8. Parse baseline/live reports, validate live report and mapping document, calculate deltas, and write both summary copies.
9. Print `FINAL_ACCEPTANCE status=PASS` or `FINAL_ACCEPTANCE status=FAIL` and relevant paths.
10. Return `0` on PASS and `2` on FAIL.

- [ ] **Step 4: Run focused and full tests**

Run:

```bash
python -m unittest tests.test_final_acceptance_runner -v
python -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add scripts/final_acceptance_runner.py tests/test_final_acceptance_runner.py
git commit -m "feat: add one-shot live acceptance runner"
```

---

### Task 4: Verify branch and document the handoff

**Files:**
- Modify: PR #6 conversation only; no production file changes required.

**Interfaces:**
- User command: `python -u scripts\final_acceptance_runner.py`

- [ ] **Step 1: Confirm GitHub Actions GREEN for the final commit**

Expected: compile and complete unit-test job succeed.

- [ ] **Step 2: Confirm PR remains Draft and unmerged**

Expected: `draft=true`, `merged=false`.

- [ ] **Step 3: Add a PR comment**

Record:

- design and plan paths;
- RED/GREEN commits;
- final command;
- offline baseline requirement;
- no automatic Ready/merge behavior.

- [ ] **Step 4: Provide one local sync/deploy/run block**

The block must sync the exact final SHA, deploy while preserving local authentication/config/input/output, and run only:

```powershell
python -u scripts\final_acceptance_runner.py
```

The user should need no additional local decision or scanner command.