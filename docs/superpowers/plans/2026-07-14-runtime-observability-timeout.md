# IEPMS Runtime Observability and Timeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give OpenClaw deterministic runtime states and a configurable 10-minute live-export window while preserving fail-closed report publication.

**Architecture:** Add a focused runtime-state module for positive CLI validation, state-line formatting, and monotonic deadline calculations. The legacy analyzer uses that module only around authentication and export polling; the safe runner forwards configuration, measures run timings, fixes conversion-failure detection, and writes runtime metadata into the manifest.

**Tech Stack:** Python 3.11 standard library, `unittest`, existing requests/pandas/openpyxl runtime.

## Global Constraints

- Default live export timeout is exactly 600 seconds.
- Default polling interval is exactly 5 seconds.
- Timeout and interval must be positive integers.
- Live runs remain fail-closed when any expected XLSX or CSV is missing or stale.
- Do not change milestone mappings, project IDs, DU IDs, View IDs, calculations, or SLA thresholds.
- `RUN_STATE` lines must remain one-line machine-readable text beginning with `RUN_STATE stage=`.
- `WAITING_FOR_AUTH` time must not be interpreted as a processing hang.
- Correct the converter marker so `Failed to convert <filename>:` fails closed.

---

### Task 1: Runtime state and deadline utility

**Files:**
- Create: `scripts/runtime_state.py`
- Create: `tests/test_runtime_state.py`

**Interfaces:**
- Produces: `positive_int(value: str) -> int`
- Produces: `emit_run_state(stage: str, **fields) -> str`
- Produces: `PollWindow(timeout_seconds: int, interval_seconds: int, monotonic=time.monotonic, sleeper=time.sleep)`
- Produces: `PollWindow.snapshot(pending_names: Iterable[str]) -> dict`
- Produces: `PollWindow.expired() -> bool`
- Produces: `PollWindow.sleep() -> float`

- [ ] **Step 1: Write failing tests**

Test that zero and negative CLI values raise `argparse.ArgumentTypeError`; state fields serialize deterministically; a fake monotonic clock produces elapsed and remaining seconds; sleep never exceeds remaining time; expiry is based on elapsed time rather than an attempt counter.

- [ ] **Step 2: Run the focused tests and confirm failure**

```text
python -m unittest tests.test_runtime_state -v
```

Expected: import failure because `scripts.runtime_state` does not exist.

- [ ] **Step 3: Implement the utility**

Use `time.monotonic` and `time.sleep` defaults, integer display values rounded down for elapsed and up for remaining, comma-separated pending names, and immediate flush for state output.

- [ ] **Step 4: Run focused tests**

```text
python -m unittest tests.test_runtime_state -v
```

Expected: all runtime-state tests pass.

- [ ] **Step 5: Commit**

```text
feat: add runtime state and polling deadline utility
```

### Task 2: Legacy analyzer time-based polling and phase states

**Files:**
- Modify: `scripts/IEPMS_Milestone_Analyzer.py`
- Modify: `tests/test_runtime_state.py`

**Interfaces:**
- Consumes: `positive_int`, `emit_run_state`, and `PollWindow`.
- Changes: `execute_api_fetch_workflow(script_dir, input_dir, fetch_timeout_seconds=600, poll_interval_seconds=5) -> bool`
- Adds hidden CLI arguments `--fetch-timeout-seconds` and `--poll-interval-seconds`.

- [ ] **Step 1: Add failing source-level contract tests**

Verify the analyzer parser exposes both options, passes them into `execute_api_fetch_workflow`, and no longer contains `max_polls = 24`.

- [ ] **Step 2: Run tests and confirm failure**

```text
python -m unittest tests.test_runtime_state -v
```

Expected: assertions fail against the fixed-attempt implementation.

- [ ] **Step 3: Implement minimum legacy changes**

Emit `WAITING_FOR_AUTH` before the local server loop and `AUTHENTICATED` after successful sync. Emit `SUBMITTING_EXPORTS`, create `PollWindow` after submissions, emit `POLLING` before each sleep/query cycle with elapsed/remaining/pending fields, and stop when the window expires. Emit `CONVERTING` before XLSX conversion and `ANALYZING` before mappings/report generation. Preserve all report logic.

- [ ] **Step 4: Run focused and syntax tests**

```text
python -m py_compile scripts/IEPMS_Milestone_Analyzer.py scripts/runtime_state.py
python -m unittest tests.test_runtime_state -v
```

Expected: syntax passes and focused tests pass.

- [ ] **Step 5: Commit**

```text
feat: make IEPMS export polling time based
```

### Task 3: Safe runner configuration, timing metadata, and converter regression

**Files:**
- Modify: `scripts/iepms_safe_runner.py`
- Modify: `scripts/run_contract.py`
- Modify: `tests/test_safe_runner.py`
- Modify: `tests/test_run_contract.py`

**Interfaces:**
- Safe-runner parser exposes `--fetch-timeout-seconds` and `--poll-interval-seconds` using `positive_int`.
- Safe runner forwards both options to the analyzer.
- `write_manifest(..., timings: Optional[dict] = None, runtime: Optional[dict] = None)` writes schema version 2.
- Failure and success manifests contain `timings.total_seconds`, `timings.analyzer_seconds`, `timings.verification_seconds`, `runtime.fetch_timeout_seconds`, and `runtime.poll_interval_seconds`.

- [ ] **Step 1: Add failing tests**

Add tests for defaults and overrides, forwarded command arguments, success/failure timing metadata, `STARTING`/`FAILED`/`SUCCESS` state output, and the exact legacy converter output `Failed to convert MW_EOS_Swap.xlsx: broken workbook` causing fail-closed behavior even when all expected files are fresh and non-empty.

- [ ] **Step 2: Run tests and confirm failure**

```text
python -m unittest tests.test_safe_runner tests.test_run_contract -v
```

Expected: new assertions fail.

- [ ] **Step 3: Implement safe-runner and manifest changes**

Measure with `time.monotonic`. Start total timing before context creation, analyzer timing immediately before `_run_analyzer`, and verification timing immediately after analyzer completion. Pass current timing/runtime dictionaries to every failure path and final success. Change the marker to `Failed to convert` so filenames between the phrase and colon are matched.

- [ ] **Step 4: Run focused tests**

```text
python -m unittest tests.test_safe_runner tests.test_run_contract -v
```

Expected: all focused tests pass.

- [ ] **Step 5: Commit**

```text
fix: record verified runtime metadata and conversion failures
```

### Task 4: Agent contract documentation

**Files:**
- Modify: `README.md`
- Modify: `SKILL.md`
- Modify: `iepms_skill/SKILL.md`

**Interfaces:**
- Both skill files remain byte-identical.
- Documents supported default command and optional timeout overrides.
- Documents exact state interpretation and failure/success markers.

- [ ] **Step 1: Update documentation**

Document that `POLLING` is a heartbeat, `WAITING_FOR_AUTH` requires Bookmarklet action and is not a hang, 30 seconds without state output is an abnormal-silence warning only, exit code 2/`FAILED` is final failure, and success requires exit code 0 plus verified marker and manifest.

- [ ] **Step 2: Verify skill parity**

```text
python -c "from pathlib import Path; assert Path('SKILL.md').read_bytes() == Path('iepms_skill/SKILL.md').read_bytes()"
```

Expected: exit code 0.

- [ ] **Step 3: Commit**

```text
docs: define OpenClaw runtime state contract
```

### Task 5: Full verification and draft PR

**Files:**
- Verify: `.github/workflows/tests.yml`
- Create: Draft PR from `feat/runtime-observability-timeout` to `main`

- [ ] **Step 1: Run complete verification**

```text
python -m py_compile scripts/IEPMS_Milestone_Analyzer.py scripts/iepms_safe_runner.py scripts/run_contract.py scripts/runtime_state.py
python -m unittest discover -s tests -v
```

Expected: all tests pass with zero failures.

- [ ] **Step 2: Confirm protected legacy values**

Confirm the diff does not change `VERIFIED_MAPPINGS`, `PROJECT_CONFIGS`, milestone keywords, report formulas, or SLA thresholds.

- [ ] **Step 3: Open Draft PR**

The PR body must link Issue #3, include the two observed 185-second failures, test evidence, scope protection, the post-merge converter-marker regression fix, and a Windows/ZTE VPN Live UAT checklist.

- [ ] **Step 4: Stop at UAT**

Do not mark ready or merge until a real OpenClaw live run verifies a slow `2023_TX_Rollout` can complete inside the extended timeout and the manifest contains runtime metadata.