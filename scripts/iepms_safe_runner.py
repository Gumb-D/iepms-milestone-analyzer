import argparse
import os
import shutil
import subprocess
import sys
import time
from typing import List, Optional

try:
    from .live_fetch import fetch_latest_exports
    from .run_contract import (
        LIVE_FETCH,
        OFFLINE_LOCAL,
        create_run_context,
        update_latest_pointer,
        verify_downloaded_files,
        verify_fresh_files,
        write_manifest,
    )
    from .runtime_state import emit_run_state, positive_int
except ImportError:  # Direct script execution
    from live_fetch import fetch_latest_exports
    from run_contract import (
        LIVE_FETCH,
        OFFLINE_LOCAL,
        create_run_context,
        update_latest_pointer,
        verify_downloaded_files,
        verify_fresh_files,
        write_manifest,
    )
    from runtime_state import emit_run_state, positive_int

EXPECTED_EXPORTS = [
    "2023_TX_Rollout",
    "2024_Celcomdigi_BAU",
    "Jendela_TX_Migration",
    "TX_Mini_Project",
    "MW_EOS_Swap",
    "ZTE_TX_MINI",
]
EXPECTED_REPORT_MODELS = [name.replace("_", " ") for name in EXPECTED_EXPORTS]

FETCH_FAILURE_MARKERS = (
    "API fetch failed or was incomplete",
    "timed out or failed to export",
    "Failed to convert",
    "Error processing file",
    "[FAILED]",
)


def _project_defaults():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    return script_dir, project_root


def parse_args(argv: Optional[List[str]] = None):
    script_dir, project_root = _project_defaults()
    parser = argparse.ArgumentParser(
        description="Verified fail-closed runner for the IEPMS milestone analyzer"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fetch", action="store_true", help="Require a complete fresh ZTE IEPMS download")
    mode.add_argument("--offline", action="store_true", help="Explicitly analyze existing local input files")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--input-dir", default=os.path.join(project_root, "input"))
    parser.add_argument("--output-dir", default=os.path.join(project_root, "output"))
    parser.add_argument("--docs-dir", default=os.path.join(project_root, "docs"))
    parser.add_argument(
        "--analyzer-script",
        default=os.path.join(script_dir, "IEPMS_Milestone_Analyzer.py"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--fetch-timeout-seconds",
        type=positive_int,
        default=600,
        help="Maximum elapsed time to wait for all live exports (default: 600)",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=positive_int,
        default=5,
        help="Seconds between live export polling cycles (default: 5)",
    )
    parser.add_argument("--force-detect", action="store_true")
    parser.add_argument("--force-convert", action="store_true")
    parser.add_argument("--no-convert", action="store_true")
    return parser.parse_args(argv)


def _run_analyzer(command: List[str], cwd: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    output_lines = []
    analysis_state_emitted = False
    if process.stdout is not None:
        for line in process.stdout:
            print(line, end="")
            output_lines.append(line)
            if not analysis_state_emitted and (
                "Loading milestone mapping configuration" in line
                or "Saved mapping configuration" in line
            ):
                emit_run_state("ANALYZING")
                analysis_state_emitted = True
    return_code = process.wait()
    return subprocess.CompletedProcess(
        command,
        return_code,
        stdout="".join(output_lines),
        stderr="",
    )


def _runtime_settings(args) -> dict:
    return {
        "fetch_timeout_seconds": args.fetch_timeout_seconds,
        "poll_interval_seconds": args.poll_interval_seconds,
    }


def _timings(
    run_started: float,
    *,
    fetch_seconds: float,
    analyzer_seconds: float,
) -> dict:
    total_seconds = max(0.0, time.monotonic() - run_started)
    verification_seconds = max(0.0, total_seconds - fetch_seconds - analyzer_seconds)
    return {
        "total_seconds": round(total_seconds, 3),
        "fetch_seconds": round(fetch_seconds, 3),
        "analyzer_seconds": round(analyzer_seconds, 3),
        "verification_seconds": round(verification_seconds, 3),
    }


def _failure(
    context,
    working_dir: str,
    *,
    expected_files,
    downloaded_files,
    missing_files,
    source: str,
    error: str,
    timings: dict,
    runtime: dict,
) -> int:
    shutil.rmtree(working_dir, ignore_errors=True)
    emit_run_state("FAILED", reason=error.replace(" ", "_"))
    manifest_path = write_manifest(
        context,
        status="FAILED",
        expected_files=expected_files,
        downloaded_files=downloaded_files,
        missing_files=missing_files,
        source=source,
        error=error,
        timings=timings,
        runtime=runtime,
    )
    print(f"VERIFIED_RUN_FAILED: {error}", file=sys.stderr)
    print(f"FAILED_MANIFEST: {manifest_path}", file=sys.stderr)
    return 2


def run(argv: Optional[List[str]] = None) -> int:
    run_started = time.monotonic()
    args = parse_args(argv)
    mode = LIVE_FETCH if args.fetch else OFFLINE_LOCAL
    source = "ZTE_IEPMS_API" if args.fetch else "LOCAL_INPUT"
    expected_files = EXPECTED_EXPORTS if args.fetch else []
    runtime = _runtime_settings(args)
    fetch_seconds = 0.0
    analyzer_seconds = 0.0

    emit_run_state(
        "STARTING",
        mode=mode,
        target_year=args.year,
        fetch_timeout_seconds=args.fetch_timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
    )

    os.makedirs(args.input_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)
    context = create_run_context(args.output_dir, args.year, mode)
    working_dir = os.path.join(context.run_dir, "_working")
    working_docs = os.path.join(working_dir, "docs")
    os.makedirs(working_dir, exist_ok=True)
    os.makedirs(working_docs, exist_ok=True)

    if args.fetch:
        fetch_started = time.monotonic()
        try:
            fetch_succeeded = fetch_latest_exports(
                os.path.dirname(os.path.abspath(args.analyzer_script)),
                os.path.abspath(args.input_dir),
                fetch_timeout_seconds=args.fetch_timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        except Exception as exc:
            fetch_seconds = max(0.0, time.monotonic() - fetch_started)
            return _failure(
                context,
                working_dir,
                expected_files=expected_files,
                downloaded_files=[],
                missing_files=list(expected_files),
                source=source,
                error=f"Live export fetch could not run: {exc}",
                timings=_timings(
                    run_started,
                    fetch_seconds=fetch_seconds,
                    analyzer_seconds=analyzer_seconds,
                ),
                runtime=runtime,
            )
        fetch_seconds = max(0.0, time.monotonic() - fetch_started)
        fresh_xlsx, missing_xlsx = verify_downloaded_files(
            args.input_dir,
            EXPECTED_EXPORTS,
            context.started_epoch,
        )
        if not fetch_succeeded or missing_xlsx:
            return _failure(
                context,
                working_dir,
                expected_files=expected_files,
                downloaded_files=fresh_xlsx,
                missing_files=missing_xlsx or list(expected_files),
                source=source,
                error="Live export fetch timed out, failed, or was incomplete",
                timings=_timings(
                    run_started,
                    fetch_seconds=fetch_seconds,
                    analyzer_seconds=analyzer_seconds,
                ),
                runtime=runtime,
            )

    command = [
        sys.executable,
        os.path.abspath(args.analyzer_script),
        "--year", str(args.year),
        "--input-dir", os.path.abspath(args.input_dir),
        "--output-dir", working_dir,
        "--docs-dir", working_docs,
    ]
    if args.force_detect:
        command.append("--force-detect")
    if args.force_convert:
        command.append("--force-convert")
    if args.no_convert:
        command.append("--no-convert")

    emit_run_state("CONVERTING")
    analyzer_started = time.monotonic()
    try:
        result = _run_analyzer(
            command,
            os.path.dirname(os.path.abspath(args.analyzer_script)),
        )
    except OSError as exc:
        analyzer_seconds = max(0.0, time.monotonic() - analyzer_started)
        return _failure(
            context,
            working_dir,
            expected_files=expected_files,
            downloaded_files=[],
            missing_files=list(expected_files),
            source=source,
            error=f"Analyzer could not start: {exc}",
            timings=_timings(
                run_started,
                fetch_seconds=fetch_seconds,
                analyzer_seconds=analyzer_seconds,
            ),
            runtime=runtime,
        )
    analyzer_seconds = max(0.0, time.monotonic() - analyzer_started)

    downloaded_files = []
    missing_files = []
    if args.fetch:
        fresh_xlsx, missing_xlsx = verify_downloaded_files(
            args.input_dir,
            EXPECTED_EXPORTS,
            context.started_epoch,
        )
        fresh_csv, missing_csv = verify_fresh_files(
            args.input_dir,
            EXPECTED_EXPORTS,
            context.started_epoch,
            ".csv",
        )
        downloaded_files = [
            name for name in EXPECTED_EXPORTS
            if name in fresh_xlsx and name in fresh_csv
        ]
        missing_files = [
            name for name in EXPECTED_EXPORTS
            if name in missing_xlsx or name in missing_csv
        ]

    combined_output = (result.stdout or "") + "\n" + (result.stderr or "")
    failure_marker = next((marker for marker in FETCH_FAILURE_MARKERS if marker in combined_output), None)
    if result.returncode != 0:
        return _failure(
            context,
            working_dir,
            expected_files=expected_files,
            downloaded_files=downloaded_files,
            missing_files=missing_files or list(expected_files),
            source=source,
            error=f"Analyzer exited with code {result.returncode}",
            timings=_timings(
                run_started,
                fetch_seconds=fetch_seconds,
                analyzer_seconds=analyzer_seconds,
            ),
            runtime=runtime,
        )
    if failure_marker:
        return _failure(
            context,
            working_dir,
            expected_files=expected_files,
            downloaded_files=downloaded_files,
            missing_files=missing_files,
            source=source,
            error=f"Analyzer reported failure marker: {failure_marker}",
            timings=_timings(
                run_started,
                fetch_seconds=fetch_seconds,
                analyzer_seconds=analyzer_seconds,
            ),
            runtime=runtime,
        )
    if args.fetch and missing_files:
        return _failure(
            context,
            working_dir,
            expected_files=expected_files,
            downloaded_files=downloaded_files,
            missing_files=missing_files,
            source=source,
            error="Incomplete live fetch; not all six expected exports were freshly downloaded and converted",
            timings=_timings(
                run_started,
                fetch_seconds=fetch_seconds,
                analyzer_seconds=analyzer_seconds,
            ),
            runtime=runtime,
        )

    working_report = os.path.join(working_dir, f"Milestone_Progress_Report_{args.year}.md")
    if "ANALYSIS COMPLETE!" not in combined_output:
        return _failure(
            context,
            working_dir,
            expected_files=expected_files,
            downloaded_files=downloaded_files,
            missing_files=missing_files,
            source=source,
            error="Analyzer did not confirm completion",
            timings=_timings(
                run_started,
                fetch_seconds=fetch_seconds,
                analyzer_seconds=analyzer_seconds,
            ),
            runtime=runtime,
        )
    if not os.path.isfile(working_report) or os.path.getsize(working_report) <= 0:
        return _failure(
            context,
            working_dir,
            expected_files=expected_files,
            downloaded_files=downloaded_files,
            missing_files=missing_files,
            source=source,
            error="Analyzer did not produce a non-empty report",
            timings=_timings(
                run_started,
                fetch_seconds=fetch_seconds,
                analyzer_seconds=analyzer_seconds,
            ),
            runtime=runtime,
        )
    if args.fetch:
        with open(working_report, "r", encoding="utf-8") as handle:
            report_text = handle.read()
        missing_report_exports = [
            clean_name
            for clean_name, model_name in zip(EXPECTED_EXPORTS, EXPECTED_REPORT_MODELS)
            if f"#### DU Model: {model_name}" not in report_text
        ]
        if missing_report_exports:
            return _failure(
                context,
                working_dir,
                expected_files=expected_files,
                downloaded_files=downloaded_files,
                missing_files=missing_report_exports,
                source=source,
                error="Generated report is missing one or more expected DU models",
                timings=_timings(
                    run_started,
                    fetch_seconds=fetch_seconds,
                    analyzer_seconds=analyzer_seconds,
                ),
                runtime=runtime,
            )

    os.replace(working_report, context.report_path)
    working_mapping = os.path.join(working_docs, "milestone_mappings.md")
    if os.path.isfile(working_mapping):
        os.replace(working_mapping, os.path.join(context.run_dir, "milestone_mappings.md"))
    shutil.rmtree(working_dir, ignore_errors=True)

    timings = _timings(
        run_started,
        fetch_seconds=fetch_seconds,
        analyzer_seconds=analyzer_seconds,
    )
    manifest_path = write_manifest(
        context,
        status="SUCCESS",
        expected_files=expected_files,
        downloaded_files=downloaded_files,
        missing_files=missing_files,
        source=source,
        report_path=context.report_path,
        timings=timings,
        runtime=runtime,
    )
    latest_path = update_latest_pointer(args.output_dir, manifest_path)

    emit_run_state("SUCCESS", run_id=context.run_id, mode=context.mode)
    print("\n========================================================")
    print("VERIFIED ANALYSIS COMPLETE!")
    print(f"  - Run ID: {context.run_id}")
    print(f"  - Mode: {context.mode}")
    print(f"  - Manifest: {manifest_path}")
    print(f"  - Report: {context.report_path}")
    print(f"  - Latest pointer: {latest_path}")
    print("========================================================")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
