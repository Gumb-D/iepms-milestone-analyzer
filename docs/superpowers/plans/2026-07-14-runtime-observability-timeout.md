# IEPMS Runtime Observability and Timeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give OpenClaw deterministic runtime states and a configurable 10-minute live-export window while preserving fail-closed report publication.

**Architecture:** Keep the legacy milestone analyzer unchanged. Add an isolated live-fetch module for authentication, export submission, monotonic time-based polling, and downloads; the safe runner calls that module first, then invokes the legacy analyzer without `--fetch` for conversion and report generation. A focused runtime-state module owns positive CLI validation, heartbeat formatting, and deadline calculations.

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

- [x] Write failing tests for positive integer validation, stable state formatting, elapsed/remaining calculations, and deadline-limited sleep.
- [x] Verify the tests fail before the module exists.
- [x] Implement the minimum runtime-state utility.
- [x] Verify focused tests pass.

### Task 2: Isolated time-based live export fetcher

**Files:**
- Create: `scripts/live_fetch.py`
- Create: `tests/test_live_fetch.py`
- Preserve unchanged: `scripts/IEPMS_Milestone_Analyzer.py`

**Interfaces:**
- Consumes: legacy `PROJECT_CONFIGS` and `run_auth_server` without modifying them.
- Produces: `fetch_latest_exports(script_dir, input_dir, fetch_timeout_seconds=600, poll_interval_seconds=5, ...) -> bool`
- Produces: `_poll_pending_files(...) -> bool` for network-free deadline testing.

- [x] Write failing tests proving polling is controlled by elapsed time and emits pending-export heartbeats.
- [x] Verify the tests fail before `scripts/live_fetch.py` exists.
- [x] Implement authentication validation/sync, export submission, monotonic polling, and downloads.
- [x] Verify successful download and timeout tests pass.
- [x] Confirm the legacy analyzer remains unchanged.

### Task 3: Safe runner runtime contract and manifest metadata

**Files:**
- Modify: `scripts/iepms_safe_runner.py`
- Modify: `scripts/run_contract.py`
- Modify: `tests/test_safe_runner.py`
- Create: `tests/test_safe_runner_runtime.py`

**Interfaces:**
- Safe-runner parser exposes `--fetch-timeout-seconds` and `--poll-interval-seconds` using `positive_int`.
- Live mode calls `fetch_latest_exports` before invoking the legacy analyzer without `--fetch`.
- `write_manifest(..., timings: Optional[dict] = None, runtime: Optional[dict] = None)` writes schema version 2.
- Success and failure manifests contain `total_seconds`, `fetch_seconds`, `analyzer_seconds`, and `verification_seconds` plus both runtime settings.

- [x] Write failing tests for defaults, overrides, fetch argument forwarding, timing metadata, and exact legacy conversion-error output.
- [x] Verify the new tests fail before implementation.
- [x] Implement live-fetch orchestration and runtime timing.
- [x] Change the conversion failure marker to `Failed to convert` so filenames between the phrase and colon are matched.
- [x] Adapt existing fail-closed tests to mock the isolated live fetcher.
- [x] Verify all safe-runner and manifest tests pass.

### Task 4: OpenClaw runtime-state documentation and CI

**Files:**
- Modify: `README.md`
- Modify: `SKILL.md`
- Modify: `iepms_skill/SKILL.md`
- Modify: `.github/workflows/tests.yml`

**Interfaces:**
- Both skill files remain byte-identical.
- Documentation defines the default command, optional timeout overrides, heartbeat interpretation, and final success/failure rules.
- CI compiles all five Python modules and runs the complete unit-test suite.

- [x] Document `WAITING_FOR_AUTH`, `POLLING`, `CONVERTING`, `ANALYZING`, `SUCCESS`, and `FAILED` states.
- [x] Document that 30 seconds without output is an abnormal-silence warning only, not automatic failure.
- [x] Document schema version 2 runtime and timing fields.
- [x] Keep root and packaged skill playbooks byte-identical.
- [x] Expand CI compilation to include `live_fetch.py` and `runtime_state.py`.

### Task 5: Full verification, review, and Live UAT gate

**Files:**
- Verify: all changed files in Draft PR #4.

- [x] Run complete GitHub Actions verification with zero failures.
- [x] Confirm the legacy analyzer blob is unchanged from `main`.
- [x] Confirm root and packaged skill playbooks have the same blob SHA.
- [x] Open Draft PR #4 linked to Issue #3.
- [ ] Complete Codex review and address any technically valid feedback.
- [ ] Synchronize the feature branch into the OpenClaw skill directory without overwriting local authentication, inputs, or outputs.
- [ ] Run one real Windows/ZTE VPN/OpenClaw live execution using the default 600-second timeout.
- [ ] Confirm a slow `2023_TX_Rollout` either completes within the window or fails with explicit remaining/pending state rather than an ambiguous hang.
- [ ] Confirm the successful manifest contains schema version 2 runtime and timing metadata.
- [ ] Mark PR ready and merge only after Live UAT passes.

## Live UAT command

```text
python -u scripts/iepms_safe_runner.py --fetch --year 2026
```

Expected success evidence:

```text
RUN_STATE stage=SUCCESS
VERIFIED ANALYSIS COMPLETE!
exit code 0
```

The verified manifest must show `status: SUCCESS`, `mode: LIVE_FETCH`, six downloaded exports, no missing files, runtime defaults `600` and `5`, and non-negative timing fields.