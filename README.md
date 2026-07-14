# IEPMS Milestone Progress Analyzer

This project downloads ZTE IEPMS transmission data, maps milestone columns, and generates year-based progress and SLA reports.

> [!IMPORTANT]
> **ZTE NETWORK CONSTRAINT**
> Live download requires the ZTE Corporate Network or ZTE VPN. Requests to `iepms.zte.com.cn` will fail outside that environment.

## Safety Model

Use `scripts/iepms_safe_runner.py` as the supported entry point. It wraps the legacy analyzer with a fail-closed verification layer.

The safe runner:

- requires an explicit `--fetch` or `--offline` mode;
- isolates each execution under `output/runs/<run_id>/`;
- requires all six configured XLSX exports and their converted CSV inputs to be newly generated and non-empty in live mode;
- rejects analyzer warnings, conversion errors, file-processing errors, non-zero exits, incomplete inputs, and missing reports;
- writes a machine-readable `manifest.json` for every run;
- updates `output/latest.json` only after a verified successful run;
- never publishes a report from a failed live fetch.

The legacy `scripts/IEPMS_Milestone_Analyzer.py` remains the calculation engine. Do not use it directly for automated reporting because it can continue with existing local files after a fetch failure.

## Directory Layout

- `input/`: Local XLSX and generated CSV inputs. Ignored by Git.
- `scripts/IEPMS_Milestone_Analyzer.py`: Existing milestone and SLA calculation engine.
- `scripts/iepms_safe_runner.py`: Supported fail-closed execution entry point.
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

Live success requires these six exports to be downloaded during the current execution:

1. `2023_TX_Rollout.xlsx`
2. `2024_Celcomdigi_BAU.xlsx`
3. `Jendela_TX_Migration.xlsx`
4. `TX_Mini_Project.xlsx`
5. `MW_EOS_Swap.xlsx`
6. `ZTE_TX_MINI.xlsx`

Each export must also produce a corresponding fresh, non-empty `.csv` file during the same run. The report is rejected when an XLSX or CSV is missing, empty, stale, fails conversion, or raises a file-processing error.

On failure, the command exits with code `2`, writes a failed manifest, removes the working report, and leaves `output/latest.json` unchanged.

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

When the underlying analyzer displays `Waiting for sync request...`:

1. Open the ZTE IEPMS page in the browser connected to ZTE VPN.
2. Click the configured `Sync Auth` bookmarklet.
3. The analyzer resumes after the cookie is written to `scripts/api_auth.json`.

Bookmarklet URL:

```javascript
javascript:(async()=>{try{const r=await fetch('http://localhost:18290/sync',{method:'POST',body:document.cookie});const d=await r.json();if(d.status==='success')alert('ZTE EPMS Auth Sync Successful');else alert('Sync Failed');}catch(e){alert('Could not connect. Run the Python command first.');}})()
```

## Verified Output Contract

A successful run prints:

```text
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
5. For live mode, confirm `expected_files` exactly equals `downloaded_files` and `missing_files` is empty.
6. Read only the report specified by `report_path`.

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
python -m py_compile scripts/IEPMS_Milestone_Analyzer.py scripts/iepms_safe_runner.py scripts/run_contract.py
```

The tests use temporary directories and mocked analyzer execution. They do not require ZTE network access or credentials.
