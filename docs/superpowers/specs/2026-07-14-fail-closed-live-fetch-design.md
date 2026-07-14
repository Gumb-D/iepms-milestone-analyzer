# Fail-Closed Live Fetch Design

## Objective

Prevent the analyzer or its agent playbooks from presenting stale, simulated, or fabricated IEPMS results when a live ZTE EPMS fetch fails, is incomplete, or cannot be verified as belonging to the current execution.

## Scope

This change covers the analyzer CLI, run metadata, output lifecycle, tests, README, and both skill playbooks. It does not redesign authentication or change milestone/SLA calculations.

## Selected Approach

Use an explicit execution-mode contract with fail-closed live mode and opt-in offline mode.

- `--fetch` means `LIVE_FETCH`: every configured export must be freshly downloaded during the current run.
- `--offline` means `OFFLINE_LOCAL`: existing local input files may be analyzed without a live fetch.
- Running without either mode is rejected to remove ambiguous fallback behavior.
- A live-fetch failure exits non-zero before conversion, analysis, report generation, or latest-pointer updates.

This is preferred over deleting old reports because deleting destroys the last valid result and still does not prove that a new report came from the current run. It is also preferred over timestamp-only checking because timestamps alone cannot prove completeness across all expected files.

## Run Lifecycle

1. Create a unique run ID using Malaysia time in `YYYYMMDDTHHMMSS+0800` form.
2. Record start time, target year, mode, expected export names, and output paths in memory.
3. For `LIVE_FETCH`, submit and download every configured export.
4. Verify that every expected file was downloaded during this run and is non-empty.
5. If verification fails:
   - write a failed manifest under the run directory;
   - return a non-zero exit code;
   - do not generate a report;
   - do not update `output/latest.json`.
6. If verification succeeds, convert and analyze inputs using existing business logic.
7. Write the report into the run directory.
8. Write a success manifest containing exact source and output metadata.
9. Atomically update `output/latest.json` to point to the successful manifest.

## Output Structure

```text
output/
  runs/
    <run_id>/
      manifest.json
      Milestone_Progress_Report_<year>.md
  latest.json
```

The legacy fixed report path is no longer the authoritative source for agent responses. The latest pointer is updated only after a fully successful run.

## Manifest Contract

Required fields:

- `schema_version`
- `run_id`
- `status`: `SUCCESS` or `FAILED`
- `mode`: `LIVE_FETCH` or `OFFLINE_LOCAL`
- `target_year`
- `started_at`
- `completed_at`
- `expected_files`
- `downloaded_files`
- `missing_files`
- `report_path`
- `source`
- `error`

For `LIVE_FETCH`, `status=SUCCESS` requires `downloaded_files` to exactly match `expected_files` and `missing_files` to be empty.

## Agent Safety Contract

Both skill playbooks must enforce:

1. Never fabricate, estimate, simulate, reconstruct, or reuse remembered IEPMS figures.
2. Never present a report unless the current command exits successfully.
3. Read `output/latest.json`, then read the referenced manifest.
4. Confirm the manifest run ID belongs to the current execution, has `status=SUCCESS`, and matches the requested year and execution mode.
5. In live mode, confirm expected and downloaded file sets match exactly.
6. Copy tables only from the report path declared by the verified manifest.
7. On any failure, return the factual error only; do not fall back to old files or old reports.

## Error Handling

- Authentication wait remains interactive, but cancellation, timeout, unauthorized responses, export failures, missing records, incomplete downloads, and zero-byte files are live-fetch failures.
- Failed runs preserve their manifest for diagnosis.
- Existing successful runs remain untouched.
- Offline mode clearly labels the source as local and must not claim that data is latest.

## Testing Strategy

Automated tests will cover:

- incomplete live fetch returns non-zero;
- incomplete live fetch does not generate a report;
- incomplete live fetch does not update `latest.json`;
- successful live fetch writes a valid success manifest;
- offline mode is explicit and writes `OFFLINE_LOCAL` metadata;
- ambiguous invocation without `--fetch` or `--offline` is rejected;
- existing progress and SLA generation remains callable for valid local fixtures.

Network calls will be isolated behind testable functions and mocked. Tests will use temporary directories and no ZTE credentials.

## Compatibility and Migration

- Existing commands using `--fetch` continue to work when all downloads succeed.
- Existing commands without `--fetch` must add `--offline`.
- Agent consumers must switch from the fixed report path to the manifest-declared report path.
- No change is made to milestone mapping or SLA thresholds.

## Acceptance Criteria

- The analyzer cannot print `ANALYSIS COMPLETE` after a failed live fetch.
- No failed live run can overwrite or supersede the last successful run.
- Every presented live report can be traced to a successful current-run manifest.
- Skill instructions explicitly prohibit generated fallback data.
- Tests pass without network access.