# IEPMS Runtime Observability and Timeout Design

## Context

Two consecutive OpenClaw live runs completed deterministically after about 185 seconds with exit code 2 because `2023_TX_Rollout` remained pending through the legacy fixed polling window of 24 attempts at 5-second intervals. Five other exports completed normally. The process was not hung, but the agent had no explicit machine-readable state model and therefore had to infer whether it was waiting, progressing, or failed.

## Goals

- Replace the fixed polling-attempt limit with a configurable elapsed-time limit.
- Make each runtime phase explicit and machine-readable.
- Preserve fail-closed publication rules.
- Record enough timing data to establish a reliable baseline after successful runs.
- Keep milestone mappings, calculations, project identifiers, DU identifiers, View identifiers, and SLA thresholds unchanged.

## Non-goals

- Do not change report calculations or business logic.
- Do not accept partial live exports.
- Do not reuse stale files when a live export times out.
- Do not add background execution or asynchronous delivery.

## CLI contract

The supported safe runner remains:

```text
python scripts/iepms_safe_runner.py --fetch --year 2026
```

It gains two live-fetch options:

```text
--fetch-timeout-seconds 600
--poll-interval-seconds 5
```

Both values must be positive integers. Defaults are 600 seconds and 5 seconds. Offline mode accepts the arguments for parser consistency but does not use them.

## Runtime state protocol

The process emits one-line states using this stable prefix:

```text
RUN_STATE stage=<STAGE> key=value ...
```

Stages:

- `STARTING`: safe runner initialized.
- `WAITING_FOR_AUTH`: local authentication sync server is waiting for the Bookmarklet.
- `AUTHENTICATED`: authentication sync completed.
- `SUBMITTING_EXPORTS`: export requests are being submitted.
- `POLLING`: exports are being generated or downloaded.
- `CONVERTING`: fresh XLSX files are being converted to CSV.
- `ANALYZING`: report generation is running.
- `SUCCESS`: verified report and manifest were published.
- `FAILED`: the run ended fail-closed.

Polling output includes:

```text
RUN_STATE stage=POLLING elapsed_seconds=125 remaining_seconds=475 pending_count=1 pending=2023_TX_Rollout
```

`pending` is a comma-separated list without spaces. Values are intended for agent parsing, not prose presentation.

## Timeout model

Polling begins after all export submissions have been attempted. A monotonic deadline is calculated from `fetch_timeout_seconds`. Each loop:

1. Emit current `POLLING` state.
2. Sleep for the lesser of the configured interval and remaining time.
3. Query export records and download completed files.
4. Stop successfully when no files remain pending.
5. Stop fail-closed when remaining time reaches zero.

The loop is controlled by elapsed time, not attempt count. Network request time contributes to elapsed time.

## Agent interpretation rules

- `WAITING_FOR_AUTH` means user action is required and must not count toward a processing-hang timeout.
- Any new `RUN_STATE` line is a heartbeat.
- During active processing, 30 seconds without output is an abnormal-silence warning, not an automatic failure.
- `VERIFIED_RUN_FAILED`, `RUN_STATE stage=FAILED`, or exit code 2 means failure immediately.
- Success requires exit code 0, `VERIFIED ANALYSIS COMPLETE!`, `RUN_STATE stage=SUCCESS`, and a `SUCCESS` manifest in `LIVE_FETCH` mode.
- The agent must read only the report referenced by that manifest.

## Timing data

Each manifest gains:

```json
{
  "timings": {
    "total_seconds": 0.0,
    "analyzer_seconds": 0.0,
    "verification_seconds": 0.0
  },
  "runtime": {
    "fetch_timeout_seconds": 600,
    "poll_interval_seconds": 5
  }
}
```

The safe runner can measure analyzer and verification time reliably. Authentication, export, conversion, and analysis phase timing will be inferred from timestamped `RUN_STATE` output during benchmark collection; the legacy analyzer does not expose structured callbacks.

## Implementation boundary

The legacy analyzer receives the timeout and interval through two new hidden CLI arguments passed by the safe runner. The only changes inside the legacy analyzer are:

- parse the two values;
- emit state lines around existing phases;
- replace `max_polls` with a monotonic deadline.

All mapping and report-generation code remains byte-for-byte unchanged outside the minimum polling and state-output areas.

## Failure handling

- Timeout leaves the pending export names in the failed manifest.
- A partial report created by the legacy analyzer remains quarantined and is deleted by the safe runner.
- `output/latest.json` is updated only after full verification succeeds.
- Existing failure markers remain authoritative.

## Testing

Automated tests cover:

- CLI defaults and overrides;
- positive integer validation;
- forwarding options from safe runner to analyzer;
- time-based polling success and timeout with mocked monotonic time and sleep;
- polling `RUN_STATE` fields;
- success and failure manifest timing/runtime metadata;
- all existing fail-closed behavior.

A Windows/ZTE VPN Live UAT remains required before merge.