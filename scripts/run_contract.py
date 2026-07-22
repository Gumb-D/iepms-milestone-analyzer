import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Tuple


LIVE_FETCH = "LIVE_FETCH"
OFFLINE_LOCAL = "OFFLINE_LOCAL"
MALAYSIA_TZ = timezone(timedelta(hours=8))
FILESYSTEM_TIMESTAMP_GRANULARITY_SECONDS = 1.0


@dataclass(frozen=True)
class RunContext:
    run_id: str
    mode: str
    target_year: int
    started_at: str
    started_epoch: float
    run_dir: str
    manifest_path: str
    report_path: str


def _atomic_write_json(path: str, payload: dict) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(temp_path, path)
    return path


def create_run_context(
    output_dir: str,
    target_year: int,
    mode: str,
    now: Optional[datetime] = None,
) -> RunContext:
    current = now or datetime.now(MALAYSIA_TZ)
    if current.tzinfo is None:
        current = current.replace(tzinfo=MALAYSIA_TZ)
    else:
        current = current.astimezone(MALAYSIA_TZ)

    base_run_id = current.strftime("%Y%m%dT%H%M%S%z")
    run_id = base_run_id
    runs_dir = os.path.join(os.path.abspath(output_dir), "runs")
    run_dir = os.path.join(runs_dir, run_id)
    suffix = 1
    while os.path.exists(run_dir):
        run_id = f"{base_run_id}-{suffix:02d}"
        run_dir = os.path.join(runs_dir, run_id)
        suffix += 1
    os.makedirs(run_dir, exist_ok=False)

    return RunContext(
        run_id=run_id,
        mode=mode,
        target_year=target_year,
        started_at=current.isoformat(),
        started_epoch=current.timestamp() if now is not None else time.time(),
        run_dir=run_dir,
        manifest_path=os.path.join(run_dir, "manifest.json"),
        report_path=os.path.join(run_dir, f"Milestone_Progress_Report_{target_year}.md"),
    )


def verify_fresh_files(
    input_dir: str,
    expected_files: Iterable[str],
    run_started_epoch: float,
    extension: str,
) -> Tuple[List[str], List[str]]:
    downloaded = []
    missing = []
    for clean_name in expected_files:
        path = os.path.join(input_dir, f"{clean_name}{extension}")
        try:
            stat = os.stat(path)
        except FileNotFoundError:
            missing.append(clean_name)
            continue

        timestamp_is_stale = (
            stat.st_mtime + FILESYSTEM_TIMESTAMP_GRANULARITY_SECONDS
            < run_started_epoch
        )
        if stat.st_size <= 0 or timestamp_is_stale:
            missing.append(clean_name)
            continue
        downloaded.append(clean_name)
    return downloaded, missing


def verify_downloaded_files(
    input_dir: str,
    expected_files: Iterable[str],
    run_started_epoch: float,
) -> Tuple[List[str], List[str]]:
    return verify_fresh_files(input_dir, expected_files, run_started_epoch, ".xlsx")


def write_manifest(
    context: RunContext,
    *,
    status: str,
    expected_files: Iterable[str],
    downloaded_files: Iterable[str],
    missing_files: Iterable[str],
    source: str,
    report_path: Optional[str] = None,
    error: Optional[str] = None,
    timings: Optional[dict] = None,
    runtime: Optional[dict] = None,
) -> str:
    payload = {
        "schema_version": 2,
        "run_id": context.run_id,
        "status": status,
        "mode": context.mode,
        "target_year": context.target_year,
        "started_at": context.started_at,
        "completed_at": datetime.now(MALAYSIA_TZ).isoformat(),
        "expected_files": list(expected_files),
        "downloaded_files": list(downloaded_files),
        "missing_files": list(missing_files),
        "report_path": os.path.abspath(report_path) if report_path else None,
        "source": source,
        "error": error,
        "timings": dict(timings or {}),
        "runtime": dict(runtime or {}),
    }
    return _atomic_write_json(context.manifest_path, payload)


def update_latest_pointer(output_dir: str, manifest_path: str) -> str:
    pointer_path = os.path.join(os.path.abspath(output_dir), "latest.json")
    return _atomic_write_json(
        pointer_path,
        {"manifest_path": os.path.abspath(manifest_path)},
    )
