# IEPMS Milestone Progress Analyzer

This project downloads ZTE IEPMS transmission data, maps milestone columns, and generates year-based progress and SLA reports.

> [!IMPORTANT]
> **ZTE NETWORK CONSTRAINT**
> Live download requires the ZTE Corporate Network or ZTE VPN. Requests to `iepms.zte.com.cn` will fail outside that environment.

## Safety Model

Use `scripts/iepms_safe_runner.py` as the supported entry point. It owns live export retrieval and wraps the legacy analyzer with a fail-closed verification layer.

The safe runner:

- requires an explicit `--fetch` or `--offline` mode;
- isolates each execution under `output/runs/<run_id>/`;
- waits for live exports using a configurable elapsed-time window instead of a fixed attempt count;
- emits machine-readable `RUN_STATE` heartbeat lines;
- requires all six configured XLSX exports and their converted CSV inputs to be newly generated and non-empty in live mode;
- rejects export timeouts, conversion errors, file-processing errors, non-zero exits, incomplete inputs, and missing reports;
- writes a machine-readable `manifest.json` with runtime settings and measured phase durations;
- updates `output/latest.json` only after a verified successful run;
- never publishes a report from a failed live fetch.

The legacy `scripts/IEPMS_Milestone_Analyzer.py` remains the calculation engine. Do not use its `--fetch` mode directly for automated reporting because the legacy path can continue with existing local files after a fetch failure.

## Directory Layout

- `input/`: Local XLSX and generated CSV inputs. Ignored by Git.
- `scripts/IEPMS_Milestone_Analyzer.py`: Existing milestone and SLA calculation engine.
- `scripts/iepms_safe_runner.py`: Supported fail-closed execution entry point.
- `scripts/live_fetch.py`: Authentication, export submission, time-based polling, and download handling.
- `scripts/runtime_state.py`: Runtime heartbeat formatting, positive CLI validation, and monotonic polling deadline.
- `scripts/run_contract.py`: Run ID, freshness verification, manifest, and latest-pointer handling.
- `scripts/milestone_config.json`: Local column mappings. Ignored by Git.
- `scripts/api_auth.json`: Local authentication data. Ignored by Git.
- `output/runs/<run_id>/`: Verified per-run report, manifest, and mapping evidence.
- `output/latest.json`: Pointer to the most recent verified successful manifest.
- `docs/`: Documentation and design records.
- `tests/`: Network-free unit tests.

## Live Mode — Latest ZTE IEPMS Data

Run from the project root:

```bash
python scripts/iepms_safe_runner.py --fetch --year 2026
```

Default runtime controls:

```text
--fetch-timeout-seconds 600
--poll-interval-seconds 5
```

Override them only when operational evidence supports a different window:

```bash
python scripts/iepms_safe_runner.py --fetch --year 2026 --fetch-timeout-seconds 900 --poll-interval-seconds 10
```

Both values must be positive integers. The timeout is elapsed wall-clock processing time for export generation and polling. Network request time counts toward it.

Live success requires these six exports to be downloaded during the current execution:

1. `2023_TX_Rollout.xlsx`
2. `2024_Celcomdigi_BAU.xlsx`
3. `Jendela_TX_Migration.xlsx`
4. `TX_Mini_Project.xlsx`
5. `MW_EOS_Swap.xlsx`
6. `ZTE_TX_MINI.xlsx`

Each export must also produce a corresponding fresh, non-empty `.csv` file during the same run. The report is rejected when an XLSX or CSV is missing, empty, stale, fails conversion, or raises a file-processing error.

On failure, the command exits with code `2`, writes a failed manifest, removes the working report, and leaves `output/latest.json` unchanged.

## Runtime State Protocol

Every state line begins with:

```text
RUN_STATE stage=<STAGE>
```

Important stages:

```text
RUN_STATE stage=STARTING
RUN_STATE stage=WAITING_FOR_AUTH action=click_sync_auth_bookmarklet
RUN_STATE stage=AUTHENTICATED
RUN_STATE stage=SUBMITTING_EXPORTS
RUN_STATE stage=POLLING elapsed_seconds=125 remaining_seconds=475 pending_count=1 pending=2023_TX_Rollout
RUN_STATE stage=CONVERTING
RUN_STATE stage=ANALYZING
RUN_STATE stage=SUCCESS
RUN_STATE stage=FAILED
```

Interpretation rules:

- `WAITING_FOR_AUTH` means user action is required. It is not a hang and must not count toward a processing timeout.
- Each `POLLING` line is a heartbeat and includes elapsed time, remaining time, and pending exports.
- Thirty seconds without a new state or analyzer output is an abnormal-silence warning only. Do not declare failure while the process is still running.
- Exit code `2`, `RUN_STATE stage=FAILED`, or `VERIFIED_RUN_FAILED` is a final failure.
- Success requires exit code `0`, `RUN_STATE stage=SUCCESS`, `VERIFIED ANALYSIS COMPLETE!`, and a successful current-run manifest.

## Offline Mode — Explicit Local Data

Use existing local files only when intentionally requested:

```bash
python scripts/iepms_safe_runner.py --offline --year 2026
```

Offline output is marked:

```text
mode: OFFLINE_LOCAL
source: LOCAL_INPUT
```

It must not be described as the latest ZTE IEPMS data.

## Authentication Sync

When output shows either `RUN_STATE stage=WAITING_FOR_AUTH` or `Waiting for sync request...`:

1. Open the ZTE IEPMS page in the browser connected to ZTE VPN.
2. Click the configured `Sync Auth` bookmarklet.
3. The process resumes after the cookie is written to `scripts/api_auth.json`.

Bookmarklet URL:

```javascript
javascript:(async()=>{try{const r=await fetch('http://localhost:18290/sync',{method:'POST',body:document.cookie});const d=await r.json();if(d.status==='success')alert('ZTE EPMS Auth Sync Successful');else alert('Sync Failed');}catch(e){alert('Could not connect. Run the Python command first.');}})()
```

## Verified Output Contract

A successful run prints:

```text
RUN_STATE stage=SUCCESS run_id=<run_id> mode=<mode>
VERIFIED ANALYSIS COMPLETE!
Run ID: <run_id>
Mode: LIVE_FETCH or OFFLINE_LOCAL
Manifest: <manifest_path>
Report: <report_path>
```

Consumers must then:

1. Read `output/latest.json`.
2. Read the referenced manifest.
3. Confirm `status` is `SUCCESS`.
4. Confirm `run_id`, `target_year`, and `mode` match the command just executed.
5. Confirm `runtime.fetch_timeout_seconds` and `runtime.poll_interval_seconds` match the command.
6. For live mode, confirm `expected_files` exactly equals `downloaded_files` and `missing_files` is empty.
7. Read only the report specified by `report_path`.

Manifest timing fields include:

```text
timings.total_seconds
timings.fetch_seconds
timings.analyzer_seconds
timings.verification_seconds
```

Never use a fixed legacy report path as proof that the current run succeeded.

## Detailed Backlog Site Lists

First complete and verify a safe-runner execution. Then query the already-verified local input data:

```bash
python scripts/IEPMS_Milestone_Analyzer.py --list-critical --du "MW EOS Swap" --kpi "MC_MOS" --year 2026 --stage critical
```

Supported KPI keys:

- `MC_MOS`
- `TI_L1`
- `MC_PAC`

Supported stages:

- `critical`
- `warning`
- `all`

## Other Controls

Pass these through the safe runner when needed:

```bash
python scripts/iepms_safe_runner.py --offline --year 2026 --force-convert
python scripts/iepms_safe_runner.py --offline --year 2026 --force-detect
python scripts/iepms_safe_runner.py --offline --year 2026 --no-convert
```

## Milestones

- SOW: TX Planning
- TSS: Physical Survey / TSSR Customer Approval
- MC: Material Collection
- MOS: Material On Site
- TI: Equipment Installation
- L1: Q&EHS L1 Approved
- RFS: Site Integrated / TX Integrated
- PAC: PAC Approved

## SLA Rules

- MC → MOS: 14-day SLA; warning at 10–13 days; breached at 14 days or more.
- TI → L1: 14-day SLA; warning at 10–13 days; breached at 14 days or more.
- MC → PAC: 30-day SLA; warning at 25–29 days; breached at 30 days or more.

## Tests

```bash
python -m unittest discover -s tests -v
python -m py_compile scripts/IEPMS_Milestone_Analyzer.py scripts/iepms_safe_runner.py scripts/live_fetch.py scripts/run_contract.py scripts/runtime_state.py
```

The tests use temporary directories and mocked analyzer/export execution. They do not require ZTE network access or credentials.
