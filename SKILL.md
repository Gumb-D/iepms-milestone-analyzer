---
name: iepms-milestone-analyzer
description: Safely fetches and analyzes IEPMS transmission milestone data with fail-closed verification, observable runtime states, per-run manifests, and verbatim report tables.
tools:
  - execute_command
  - read_file
---

# Instruction Playbook: Analyze IEPMS Milestone Data

> [!IMPORTANT]
> **ZTE NETWORK CONSTRAINT**
> Live fetch can only run on the ZTE Corporate Network or ZTE VPN. Outside that environment, do not claim that current IEPMS data was retrieved.

## 1. Non-Negotiable Data Safety Rules

1. Never fabricate, estimate, simulate, reconstruct, or infer IEPMS figures.
2. Never reuse figures from conversation memory, examples, prior answers, or an old fixed report path.
3. Never present analysis unless the current command exits successfully and the current-run manifest passes every verification below.
4. If fetch, authentication, export, freshness, manifest, or report verification fails, return only the factual failure and required user action.
5. Do not silently fall back from live mode to local files.
6. Offline analysis is allowed only when the user explicitly requests local or offline data, and it must be labelled `OFFLINE_LOCAL`.

## 2. Parameter Extraction

- Determine the target year from the request. Default to `2026` only when no year is stated.
- Default to live mode using `--fetch`.
- Use `--offline` only when the user explicitly asks to analyze existing local files without downloading.
- Default live runtime settings are `--fetch-timeout-seconds 600` and `--poll-interval-seconds 5`.
- Override runtime settings only when the user or an approved measured baseline requires it.

## 3. Execute Through the Safe Runner

### Live mode

```bash
python scripts/iepms_safe_runner.py --fetch --year <target_year>
```

Optional explicit runtime override:

```bash
python scripts/iepms_safe_runner.py --fetch --year <target_year> --fetch-timeout-seconds <positive_seconds> --poll-interval-seconds <positive_seconds>
```

### Explicit offline mode

```bash
python scripts/iepms_safe_runner.py --offline --year <target_year>
```

Do not use `scripts/IEPMS_Milestone_Analyzer.py --fetch` directly for automated reporting.

## 4. Runtime State and Waiting Rules

Treat every line beginning with `RUN_STATE` as a machine-readable heartbeat.

### Authentication wait

```text
RUN_STATE stage=WAITING_FOR_AUTH action=click_sync_auth_bookmarklet
```

- This means the process is waiting for human authentication, not hung.
- Do not count this period toward a processing timeout.
- Ask the user to open the ZTE IEPMS page and click the `Sync Auth` bookmarklet when browser automation is unavailable.
- Do not produce report data while authentication remains unresolved.

The process resumes with:

```text
RUN_STATE stage=AUTHENTICATED
```

### Active export processing

```text
RUN_STATE stage=POLLING elapsed_seconds=<n> remaining_seconds=<n> pending_count=<n> pending=<names>
```

- Every `POLLING` line proves the process is alive.
- Read `pending`, `elapsed_seconds`, and `remaining_seconds`; do not guess progress.
- The default export window is 600 seconds.
- Do not classify the run as failed before the process exits or emits a failure marker.
- Thirty seconds without any new state or analyzer output is an abnormal-silence warning only. Check process status; do not invent a result.

Other active stages are:

```text
RUN_STATE stage=STARTING
RUN_STATE stage=SUBMITTING_EXPORTS
RUN_STATE stage=CONVERTING
RUN_STATE stage=ANALYZING
```

### Final states

Failure is final when any of these occurs:

```text
RUN_STATE stage=FAILED
VERIFIED_RUN_FAILED
exit code 2
```

Success requires all of these:

```text
RUN_STATE stage=SUCCESS
VERIFIED ANALYSIS COMPLETE!
exit code 0
```

A final state never permits use of an older report.

## 5. Mandatory Current-Run Verification

After the command returns:

1. Require exit code `0`.
2. Require `RUN_STATE stage=SUCCESS`.
3. Require the output marker `VERIFIED ANALYSIS COMPLETE!`.
4. Capture the printed `Run ID`, `Mode`, `Manifest`, and `Report` paths.
5. Read `output/latest.json`.
6. Read the manifest referenced by `output/latest.json`.
7. Verify all of the following:
   - `schema_version` is at least `2`;
   - `status` is exactly `SUCCESS`;
   - `run_id` exactly matches the Run ID printed by the current command;
   - `target_year` matches the requested year;
   - `mode` matches the command used;
   - `report_path` matches the report path printed by the current command;
   - the report file exists and is non-empty;
   - `runtime.fetch_timeout_seconds` and `runtime.poll_interval_seconds` match the command;
   - `timings.total_seconds`, `timings.fetch_seconds`, `timings.analyzer_seconds`, and `timings.verification_seconds` exist and are non-negative.
8. For `LIVE_FETCH`, additionally verify:
   - `source` is `ZTE_IEPMS_API`;
   - `expected_files` exactly equals `downloaded_files`;
   - `missing_files` is empty;
   - all six configured exports are present in both file lists.
9. For `OFFLINE_LOCAL`, verify `source` is `LOCAL_INPUT` and clearly state that the report uses local data and is not guaranteed to be the latest portal data.

If any check fails, do not read or present the report. State the exact failed condition instead.

## 6. Read the Verified Report

Read only the file declared by the verified manifest field `report_path`.

Do not read `output/Milestone_Progress_Report_<year>.md` as an authoritative source because it may be from an older legacy run.

## 7. Respond With Verbatim Tables

Copy Markdown tables exactly from the verified report. Do not rebuild, compress, reformat, or invent tables.

Include:

- Combined Monthly Progress (All Projects).
- Progress Breakdown by Project & DU Model for each project.
- MC ➔ MOS SLA Backlog for the target year.
- TI ➔ L1 SLA Backlog for the target year.
- MC ➔ PAC SLA Backlog for the target year.

Before the tables, state:

- Run ID.
- Fetch completion time from the manifest.
- Mode.
- Source.
- Downloaded file count.
- Total runtime from `timings.total_seconds`.

## 8. Detailed Backlog Site Lists

First complete and verify a safe-runner execution for the same year and mode. Only after that verification, query the already-verified local inputs:

```bash
python scripts/IEPMS_Milestone_Analyzer.py --list-critical --du "<du_model>" --kpi "<kpi_key>" --year <target_year> --stage <stage>
```

Supported KPI keys are `MC_MOS`, `TI_L1`, and `MC_PAC`. Supported stages are `critical`, `warning`, and `all`.

Copy the resulting Markdown table verbatim. Do not convert it into prose, a comma-separated list, or a custom table.

## 9. Failure Response Contract

When the safe runner returns non-zero, prints `VERIFIED_RUN_FAILED`, emits `RUN_STATE stage=FAILED`, or produces a failed manifest:

- state that no verified current report is available;
- state the exact error and missing files from the failed manifest;
- include the measured total runtime and pending export names when available;
- do not summarize any old report;
- do not provide sample data;
- do not write phrases such as “simulation mode” unless the verified manifest explicitly contains that mode, which the current contract does not support.
