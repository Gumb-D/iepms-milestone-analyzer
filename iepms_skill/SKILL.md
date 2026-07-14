---
name: iepms-milestone-analyzer
description: Safely fetches and analyzes IEPMS transmission milestone data with fail-closed verification, per-run manifests, and verbatim report tables.
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

## 3. Execute Through the Safe Runner

### Live mode

```bash
python scripts/iepms_safe_runner.py --fetch --year <target_year>
```

### Explicit offline mode

```bash
python scripts/iepms_safe_runner.py --offline --year <target_year>
```

Do not use `scripts/IEPMS_Milestone_Analyzer.py --fetch` directly for automated reporting.

## 4. Interactive Authentication Handling

If the underlying analyzer prints `Waiting for sync request...`:

- If browser automation is available, open `https://iepms.zte.com.cn`, allow ZTE SSO/VPN authentication, obtain the browser cookie, write it to `scripts/api_auth.json`, and let the command continue.
- Otherwise stop and ask the user to open the ZTE IEPMS page and click the `Sync Auth` bookmarklet.
- Do not produce any report data while authentication remains unresolved.

## 5. Mandatory Current-Run Verification

After the command returns:

1. Require exit code `0`.
2. Require the output marker `VERIFIED ANALYSIS COMPLETE!`.
3. Capture the printed `Run ID`, `Mode`, `Manifest`, and `Report` paths.
4. Read `output/latest.json`.
5. Read the manifest referenced by `output/latest.json`.
6. Verify all of the following:
   - `status` is exactly `SUCCESS`;
   - `run_id` exactly matches the Run ID printed by the current command;
   - `target_year` matches the requested year;
   - `mode` matches the command used;
   - `report_path` matches the report path printed by the current command;
   - the report file exists and is non-empty.
7. For `LIVE_FETCH`, additionally verify:
   - `source` is `ZTE_IEPMS_API`;
   - `expected_files` exactly equals `downloaded_files`;
   - `missing_files` is empty;
   - all six configured exports are present in both file lists.
8. For `OFFLINE_LOCAL`, verify `source` is `LOCAL_INPUT` and clearly state that the report uses local data and is not guaranteed to be the latest portal data.

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

## 8. Detailed Backlog Site Lists

First complete and verify a safe-runner execution for the same year and mode. Only after that verification, query the already-verified local inputs:

```bash
python scripts/IEPMS_Milestone_Analyzer.py --list-critical --du "<du_model>" --kpi "<kpi_key>" --year <target_year> --stage <stage>
```

Supported KPI keys are `MC_MOS`, `TI_L1`, and `MC_PAC`. Supported stages are `critical`, `warning`, and `all`.

Copy the resulting Markdown table verbatim. Do not convert it into prose, a comma-separated list, or a custom table.

## 9. Failure Response Contract

When the safe runner returns non-zero, prints `VERIFIED_RUN_FAILED`, or produces a failed manifest:

- state that no verified current report is available;
- state the exact error and missing files from the failed manifest;
- do not summarize any old report;
- do not provide sample data;
- do not write phrases such as “simulation mode” unless the verified manifest explicitly contains that mode, which the current contract does not support.
