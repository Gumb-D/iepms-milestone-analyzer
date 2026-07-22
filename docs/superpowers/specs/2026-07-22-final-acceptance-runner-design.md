# Final Acceptance Runner Design

## Goal

Provide one repository command that performs the remaining guarded live validation, compares the new live report with the successful offline baseline, validates report consistency, and writes a single final acceptance summary without changing PR state or merging code.

## User Command

```powershell
python -u scripts\final_acceptance_runner.py
```

The runner defaults to year `2026` and project-local `input` / `output` directories. Optional CLI overrides exist for tests and controlled troubleshooting.

## Inputs

- Current successful offline baseline referenced by `output/latest.json` at runner start.
- Existing local authentication and live-fetch configuration used by `iepms_guarded_runner.py`.
- The six expected IEPMS exports:
  - `2023_TX_Rollout`
  - `2024_Celcomdigi_BAU`
  - `Jendela_TX_Migration`
  - `TX_Mini_Project`
  - `MW_EOS_Swap`
  - `ZTE_TX_MINI`

## Execution Flow

1. Read and validate the current `output/latest.json` baseline.
2. Require the baseline manifest to be `SUCCESS`, `OFFLINE_LOCAL`, year `2026`, with a non-empty report.
3. Execute `iepms_guarded_runner.py --fetch --year 2026 --force-convert`.
4. Require a zero exit code and markers `MAPPING_VALIDATION_COMPLETE`, `RUN_STATE stage=SUCCESS`, and `VERIFIED ANALYSIS COMPLETE!`.
5. Read the new latest manifest and require `SUCCESS`, `LIVE_FETCH`, all six expected/downloaded exports, no missing exports, and a non-empty report.
6. Parse baseline and live Markdown reports.
7. Validate report structure and arithmetic:
   - all eight milestones exist in the combined table;
   - all six DU models exist;
   - each milestone total equals its twelve monthly values;
   - each combined milestone equals the sum of six DU totals;
   - all three SLA tables exist;
   - each combined SLA count equals the sum of the DU rows.
8. Verify the live mapping document contains the required TX Mini identities:
   - `TX Mini Project / RFS = Software Commissioning / TX Integrated`;
   - `ZTE TX MINI / RFS = Software Commissioning / Site Integrated`;
   - `ZTE TX MINI / L1 = Q&EHS / L1 Approved`;
   - `ZTE TX MINI / TSS = Survey&Design / Physical Survey`.
9. Produce `Final_Acceptance_Summary_2026.md` in the live run directory and copy it to `output/Final_Acceptance_Summary_2026.md`.
10. Print a compact terminal handoff with status, run ID, manifest, report, mapping document, summary, and key TX Mini deltas.

## Acceptance Status

- `PASS`: every automated live-fetch, mapping, report-structure, arithmetic, identity, and SLA consistency check passes.
- `FAIL`: any required input, marker, file, report section, mapping identity, or arithmetic check fails.

Normal live-data changes do not fail acceptance. They are recorded as baseline-to-live deltas.

## Failure Safety

- The runner never marks a failed run as accepted.
- The guarded live runner remains the authority for fresh-file and six-export verification.
- The runner does not alter local authentication files.
- The runner does not update PR state, mark Ready, or merge.
- A failed comparison writes a failure summary when a live run directory is available and exits with code `2`.

## Files

- Create `scripts/final_acceptance_runner.py`: orchestration, report parsing, consistency checks, delta generation, summary writing.
- Create `tests/test_final_acceptance_runner.py`: parser, consistency, failure-safety, and orchestration tests.
- Create `docs/superpowers/plans/2026-07-22-final-acceptance-runner.md`: TDD implementation plan.

## Non-Goals

- No automatic PR merge.
- No automatic transition from Draft to Ready.
- No subjective business approval of changed live counts; the summary exposes the deltas for traceability.
- No new external dependencies.