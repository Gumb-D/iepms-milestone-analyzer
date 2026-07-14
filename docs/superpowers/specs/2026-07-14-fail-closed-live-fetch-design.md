# Fail-Closed Live Fetch Design

## Objective

Prevent the analyzer or its agent playbooks from presenting stale, partial, simulated, or fabricated IEPMS results when a live ZTE EPMS fetch fails, conversion fails, file processing is incomplete, or the output cannot be proven to belong to the current execution.

## Scope

This change adds a protective execution layer, per-run metadata, tests, README guidance, and agent guardrails. It intentionally leaves the existing milestone mappings, SLA thresholds, API integration, and report calculations unchanged.

## Selected Approach

Use a fail-closed wrapper around the legacy analyzer instead of refactoring its approximately 1,200-line calculation script in the first safety fix.

- `scripts/iepms_safe_runner.py` is the supported entry point.
- `scripts/IEPMS_Milestone_Analyzer.py` remains the calculation engine.
- `--fetch` means `LIVE_FETCH` and requires complete current-run evidence.
- `--offline` means `OFFLINE_LOCAL` and explicitly permits existing local inputs.
- Running without exactly one mode is rejected.

This wrapper approach minimizes regression risk while immediately blocking stale report publication. A later refactor may move the contract directly into the analyzer after live UAT proves the behavior.

## Run Lifecycle

1. Create a Malaysia-time run ID and isolated run directory.
2. Execute the legacy analyzer in a quarantine output directory under the run directory.
3. Capture its exit code, stdout, and stderr.
4. In live mode, verify all six configured exports have both:
   - a fresh, non-empty XLSX written after the run start;
   - a fresh, non-empty CSV written after the run start.
5. Reject known failure markers, including incomplete fetch, server export failure, conversion failure, and per-file processing errors.
6. Require the legacy completion marker and a non-empty quarantine report.
7. On failure:
   - delete the quarantine output;
   - write a failed manifest;
   - return exit code `2`;
   - do not update `output/latest.json`;
   - do not publish a report in the run directory.
8. On success:
   - move the report and mapping evidence into the run directory;
   - write a success manifest;
   - atomically update `output/latest.json`.

## Output Structure

```text
output/
  runs/
    <run_id>/
      manifest.json
      Milestone_Progress_Report_<year>.md
      milestone_mappings.md
  latest.json
```

Failed runs retain only diagnostic metadata. The fixed legacy report path is not authoritative.

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

For live success, `downloaded_files` contains an export name only when both its XLSX and CSV pass current-run freshness and non-empty checks. `expected_files` and `downloaded_files` must match exactly, and `missing_files` must be empty.

## Agent Safety Contract

Both skill playbooks must enforce:

1. Never fabricate, estimate, simulate, reconstruct, or reuse remembered IEPMS figures.
2. Execute through the safe runner.
3. Require exit code zero and the `VERIFIED ANALYSIS COMPLETE!` marker.
4. Read `output/latest.json`, then the referenced manifest.
5. Confirm current run ID, target year, mode, source, status, and live file-set equality.
6. Read only the report path declared by the verified manifest.
7. On any failure, return the factual error only and never fall back to an old report.

## Error Handling

Live mode fails closed for:

- analyzer start failure;
- non-zero analyzer exit;
- authentication/export failure markers;
- incomplete or stale XLSX files;
- incomplete or stale CSV files;
- XLSX-to-CSV conversion errors;
- per-file processing errors;
- missing completion marker;
- missing or empty report.

Offline mode clearly labels the source as local and must not claim that data is latest.

## Testing Strategy

Network-free `unittest` coverage verifies:

- explicit mode is mandatory;
- stale or incomplete live exports fail;
- fresh XLSX with stale/missing CSV fails;
- partial file-processing errors fail even when the legacy analyzer prints completion;
- failed runs publish no report and do not update `latest.json`;
- failed manifests preserve diagnostics;
- successful live runs require all six verified export pairs;
- successful offline runs publish `OFFLINE_LOCAL` metadata;
- JSON writes and latest-pointer replacement are atomic.

## Compatibility and Migration

- Existing live automation must change its command to `python scripts/iepms_safe_runner.py --fetch --year <year>`.
- Intentional local analysis must use `--offline`.
- Detailed backlog queries may use the legacy CLI only after a safe-runner execution has verified the input set.
- Milestone calculations and SLA thresholds remain unchanged.

## Acceptance Criteria

- A failed live run cannot publish or supersede a report.
- A report based on stale CSV inputs cannot be published.
- A partial report cannot be published when any file-processing error is reported.
- Every successful report is traceable to a current-run success manifest.
- Agent instructions explicitly prohibit generated fallback data.
- All tests pass without ZTE network access or credentials.