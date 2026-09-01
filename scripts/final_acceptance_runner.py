import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Sequence, Tuple


MILESTONES = ("SOW", "TSS", "MC", "MOS", "TI", "L1", "RFS", "PAC")
SLA_KEYS = ("MC_MOS", "TI_L1", "MC_PAC")
EXPECTED_MODELS = (
    "2023 TX Rollout",
    "2024 Celcomdigi BAU",
    "Jendela TX Migration",
    "TX Mini Project",
    "MW EOS Swap",
    "ZTE TX MINI",
)
EXPECTED_EXPORTS = (
    "2023_TX_Rollout",
    "2024_Celcomdigi_BAU",
    "Jendela_TX_Migration",
    "TX_Mini_Project",
    "MW_EOS_Swap",
    "ZTE_TX_MINI",
)
REQUIRED_MARKERS = (
    "MAPPING_VALIDATION_COMPLETE",
    "RUN_STATE stage=SUCCESS",
    "VERIFIED ANALYSIS COMPLETE!",
)
REQUIRED_MAPPING_IDENTITIES = {
    ("TX Mini Project", "RFS"): ("Software Commissioning", "TX Integrated"),
    ("ZTE TX MINI", "RFS"): ("Software Commissioning", "Site Integrated"),
    ("ZTE TX MINI", "L1"): ("Q&EHS", "L1 Approved"),
    ("ZTE TX MINI", "TSS"): ("Survey&Design", "Physical Survey"),
}


def _clean(value: object) -> str:
    return str(value or "").strip().replace("**", "").replace("`", "").strip()


def _normalise(value: object) -> str:
    return " ".join(_clean(value).lower().split())


def _split_row(line: str) -> List[str]:
    """Split a Markdown row without treating pipes inside code spans as separators."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    body = stripped[1:-1] if stripped.endswith("|") else stripped[1:]
    cells: List[str] = []
    current: List[str] = []
    in_code = False
    escaped = False
    for character in body:
        if character == "`" and not escaped:
            in_code = not in_code
            current.append(character)
        elif character == "|" and not in_code:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        escaped = character == "\\" and not escaped
        if character != "\\":
            escaped = False
    cells.append("".join(current).strip())
    return cells


def _is_separator(cells: Sequence[str]) -> bool:
    return bool(cells) and all(
        set(cell.replace(":", "").replace(" ", "")) <= {"-"}
        for cell in cells
    )


def _as_int(value: str) -> int:
    return int(_clean(value).replace(",", ""))


def _parse_progress_rows(lines: Sequence[str], start: int) -> Tuple[Dict[str, dict], int]:
    parsed: Dict[str, dict] = {}
    index = start
    while index < len(lines):
        cells = _split_row(lines[index])
        if not cells:
            break
        if _is_separator(cells):
            index += 1
            continue
        if len(cells) < 14:
            break
        milestone = _clean(cells[0])
        if milestone not in MILESTONES:
            break
        months = [_as_int(value) for value in cells[1:13]]
        parsed[milestone] = {"months": months, "total": _as_int(cells[13])}
        index += 1
    return parsed, index


def _parse_sla_rows(lines: Sequence[str], start: int) -> Tuple[Dict[str, dict], int]:
    parsed: Dict[str, dict] = {}
    index = start
    while index < len(lines):
        cells = _split_row(lines[index])
        if not cells:
            break
        if _is_separator(cells):
            index += 1
            continue
        if len(cells) < 7:
            break
        name = _clean(cells[0])
        key = "Combined" if name == "Total" else name
        parsed[key] = {
            "open": _as_int(cells[1]),
            "within": _as_int(cells[2]),
            "warning": _as_int(cells[3]),
            "breached": _as_int(cells[4]),
        }
        index += 1
    return parsed, index


def parse_report(text: str) -> dict:
    """Parse analyzer Markdown into combined, per-model, and SLA structures."""
    lines = text.splitlines()
    result = {
        "combined": {},
        "models": {},
        "sla": {key: {} for key in SLA_KEYS},
    }
    context: Optional[Tuple[str, str]] = None
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("## 1. Combined Monthly Progress"):
            context = ("combined", "")
        elif stripped.startswith("#### DU Model:"):
            model = stripped.split(":", 1)[1].strip()
            result["models"].setdefault(model, {})
            context = ("model", model)
        elif stripped.startswith("### 3.1 MC"):
            context = ("sla", "MC_MOS")
        elif stripped.startswith("### 3.2 TI"):
            context = ("sla", "TI_L1")
        elif stripped.startswith("### 3.3 MC"):
            context = ("sla", "MC_PAC")
        elif stripped.startswith("| Milestone | Jan") and context is not None:
            rows, next_index = _parse_progress_rows(lines, index + 1)
            if context[0] == "combined":
                result["combined"] = rows
            elif context[0] == "model":
                result["models"][context[1]] = rows
            index = next_index
            continue
        elif stripped.startswith("| DU Model | Open Backlog") and context is not None:
            rows, next_index = _parse_sla_rows(lines, index + 1)
            if context[0] == "sla":
                result["sla"][context[1]] = rows
            index = next_index
            continue
        index += 1
    return result


def _validate_progress_row(label: str, row: dict) -> List[str]:
    errors: List[str] = []
    months = row.get("months", [])
    total = row.get("total")
    if len(months) != 12:
        errors.append(f"{label} does not contain 12 months")
    elif total is None or any(value < 0 for value in months) or total < 0:
        errors.append(f"{label} contains negative or missing values")
    elif sum(months) != total:
        errors.append(f"{label} monthly sum does not equal total")
    return errors


def validate_report(parsed: dict, expected_models: Sequence[str] = EXPECTED_MODELS) -> List[str]:
    """Return deterministic structure and arithmetic errors for a parsed report."""
    errors: List[str] = []
    combined = parsed.get("combined", {})
    models = parsed.get("models", {})
    sla = parsed.get("sla", {})

    for milestone in MILESTONES:
        row = combined.get(milestone)
        if row is None:
            errors.append(f"missing combined {milestone} row")
        else:
            errors.extend(_validate_progress_row(f"combined {milestone}", row))

    for model in expected_models:
        model_rows = models.get(model)
        if model_rows is None:
            errors.append(f"missing DU model {model}")
            continue
        for milestone in MILESTONES:
            row = model_rows.get(milestone)
            if row is None:
                errors.append(f"missing {model} {milestone} row")
            else:
                errors.extend(_validate_progress_row(f"{model} {milestone}", row))

    for milestone in MILESTONES:
        if milestone not in combined:
            continue
        rows = [models.get(model, {}).get(milestone) for model in expected_models]
        if any(row is None for row in rows):
            continue
        model_total = sum(row["total"] for row in rows if row is not None)
        if combined[milestone]["total"] != model_total:
            errors.append(
                f"combined {milestone} total {combined[milestone]['total']} "
                f"does not equal DU sum {model_total}"
            )

    for sla_key in SLA_KEYS:
        table = sla.get(sla_key, {})
        for model in expected_models:
            if model not in table:
                errors.append(f"missing {sla_key} SLA row for {model}")
        combined_row = table.get("Combined")
        if combined_row is None:
            errors.append(f"missing {sla_key} combined SLA row")
            continue
        for name, row in table.items():
            values = [row.get(field, -1) for field in ("open", "within", "warning", "breached")]
            if any(value < 0 for value in values):
                errors.append(f"{sla_key} {name} contains negative or missing values")
            elif row["open"] != row["within"] + row["warning"] + row["breached"]:
                errors.append(f"{sla_key} {name} open backlog does not equal status sum")
        if all(model in table for model in expected_models):
            for field in ("open", "within", "warning", "breached"):
                du_sum = sum(table[model][field] for model in expected_models)
                if combined_row[field] != du_sum:
                    errors.append(
                        f"{sla_key} combined {field} {combined_row[field]} "
                        f"does not equal DU sum {du_sum}"
                    )
    return errors


def compare_reports(baseline: dict, live: dict) -> dict:
    """Return live-minus-baseline totals for combined, models, and SLA rows."""
    deltas = {"combined": {}, "models": {}, "sla": {}}
    for milestone in MILESTONES:
        deltas["combined"][milestone] = (
            live["combined"][milestone]["total"]
            - baseline["combined"][milestone]["total"]
        )
    for model in EXPECTED_MODELS:
        deltas["models"][model] = {}
        for milestone in MILESTONES:
            deltas["models"][model][milestone] = (
                live["models"][model][milestone]["total"]
                - baseline["models"][model][milestone]["total"]
            )
    for sla_key in SLA_KEYS:
        deltas["sla"][sla_key] = {}
        for field in ("open", "within", "warning", "breached"):
            deltas["sla"][sla_key][field] = (
                live["sla"][sla_key]["Combined"][field]
                - baseline["sla"][sla_key]["Combined"][field]
            )
    return deltas


def validate_mapping_document(text: str) -> List[str]:
    """Require exact stage/task identities for the critical TX Mini milestones."""
    found: Dict[Tuple[str, str], Tuple[str, str]] = {}
    section: Optional[str] = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped[3:].strip()
            continue
        cells = _split_row(line)
        if section is None or len(cells) < 6 or _is_separator(cells):
            continue
        milestone = _clean(cells[0])
        if milestone in MILESTONES:
            found[(section, milestone)] = (_clean(cells[3]), _clean(cells[4]))

    errors: List[str] = []
    for key, expected in REQUIRED_MAPPING_IDENTITIES.items():
        actual = found.get(key)
        label = f"{key[0]} {key[1]}"
        if actual is None:
            errors.append(f"missing mapping identity for {label}")
        elif tuple(_normalise(value) for value in actual) != tuple(
            _normalise(value) for value in expected
        ):
            errors.append(
                f"{label} identity mismatch: found {actual[0]} / {actual[1]}, "
                f"expected {expected[0]} / {expected[1]}"
            )
    return errors


def _signed(value: int) -> str:
    return f"{value:+d}"


def render_summary(
    *,
    status: str,
    baseline_manifest: str,
    live_manifest: str,
    live_report: str,
    mapping_document: str,
    deltas: dict,
    errors: Sequence[str],
) -> str:
    """Render deterministic Markdown acceptance evidence."""
    lines = [
        f"# Final Acceptance Summary - {status}",
        "",
        "## Evidence",
        "",
        f"- Baseline manifest: `{baseline_manifest}`",
        f"- Live manifest: `{live_manifest}`",
        f"- Live report: `{live_report}`",
        f"- Mapping document: `{mapping_document}`",
        "",
        "## Automated Checks",
        "",
    ]
    if errors:
        lines.extend(f"- [ ] {error}" for error in errors)
    else:
        lines.extend(
            [
                "- [x] Successful OFFLINE_LOCAL baseline",
                "- [x] Complete guarded LIVE_FETCH",
                "- [x] Six expected exports downloaded and converted",
                "- [x] Mapping validation complete",
                "- [x] Report structure and arithmetic consistent",
                "- [x] Critical TX Mini mapping identities correct",
                "- [x] SLA combined rows equal DU sums",
            ]
        )

    lines.extend(
        [
            "",
            "## Combined Milestone Delta (Live - Offline Baseline)",
            "",
            "| Milestone | Delta |",
            "| :--- | ---: |",
        ]
    )
    for milestone in MILESTONES:
        lines.append(f"| {milestone} | {_signed(deltas.get('combined', {}).get(milestone, 0))} |")

    lines.extend(["", "## Key DU Milestone Delta", ""])
    for model in ("TX Mini Project", "ZTE TX MINI"):
        lines.extend([f"### {model}", "", "| Milestone | Delta |", "| :--- | ---: |"])
        model_delta = deltas.get("models", {}).get(model, {})
        for milestone in MILESTONES:
            lines.append(f"| {milestone} | {_signed(model_delta.get(milestone, 0))} |")
        lines.append("")

    lines.extend(
        [
            "## Combined SLA Delta",
            "",
            "| KPI | Open | Within | Warning | Breached |",
            "| :--- | ---: | ---: | ---: | ---: |",
        ]
    )
    for sla_key in SLA_KEYS:
        row = deltas.get("sla", {}).get(sla_key, {})
        lines.append(
            f"| {sla_key} | {_signed(row.get('open', 0))} | "
            f"{_signed(row.get('within', 0))} | {_signed(row.get('warning', 0))} | "
            f"{_signed(row.get('breached', 0))} |"
        )
    lines.append("")
    return "\n".join(lines)


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _latest_manifest_path(output_dir: str) -> str:
    pointer_path = os.path.join(output_dir, "latest.json")
    manifest_path = _load_json(pointer_path).get("manifest_path")
    if not manifest_path:
        raise ValueError(f"latest pointer has no manifest_path: {pointer_path}")
    return os.path.abspath(manifest_path)


def _validate_baseline_manifest(manifest: dict, year: int) -> List[str]:
    errors = []
    if manifest.get("status") != "SUCCESS":
        errors.append("baseline manifest status is not SUCCESS")
    if manifest.get("mode") != "OFFLINE_LOCAL":
        errors.append("baseline manifest mode is not OFFLINE_LOCAL")
    if manifest.get("target_year") != year:
        errors.append(f"baseline target year is not {year}")
    report_path = manifest.get("report_path")
    if not report_path or not os.path.isfile(report_path) or os.path.getsize(report_path) <= 0:
        errors.append("baseline report is missing or empty")
    return errors


def _validate_live_manifest(manifest: dict, year: int) -> List[str]:
    errors = []
    if manifest.get("status") != "SUCCESS":
        errors.append("live manifest status is not SUCCESS")
    if manifest.get("mode") != "LIVE_FETCH":
        errors.append("live manifest mode is not LIVE_FETCH")
    if manifest.get("target_year") != year:
        errors.append(f"live target year is not {year}")
    if list(manifest.get("expected_files") or []) != list(EXPECTED_EXPORTS):
        errors.append("live manifest expected_files does not contain the exact six exports")
    if sorted(manifest.get("downloaded_files") or []) != sorted(EXPECTED_EXPORTS):
        errors.append("live manifest downloaded_files does not contain all six exports")
    if manifest.get("missing_files"):
        errors.append(f"live manifest still has missing files: {manifest.get('missing_files')}")
    report_path = manifest.get("report_path")
    if not report_path or not os.path.isfile(report_path) or os.path.getsize(report_path) <= 0:
        errors.append("live report is missing or empty")
    return errors


def _run_live_command(command: Sequence[str], cwd: str) -> subprocess.CompletedProcess:
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    lines: List[str] = []
    if process.stdout is not None:
        for line in process.stdout:
            print(line, end="")
            lines.append(line)
    return subprocess.CompletedProcess(list(command), process.wait(), stdout="".join(lines), stderr="")


def _empty_deltas() -> dict:
    return {
        "combined": {milestone: 0 for milestone in MILESTONES},
        "models": {
            model: {milestone: 0 for milestone in MILESTONES}
            for model in EXPECTED_MODELS
        },
        "sla": {
            key: {field: 0 for field in ("open", "within", "warning", "breached")}
            for key in SLA_KEYS
        },
    }


def _write_summary(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")
    os.replace(temp_path, path)


def parse_args(argv: Optional[List[str]] = None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    parser = argparse.ArgumentParser(description="One-shot final acceptance for IEPMS milestone analysis")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--input-dir", default=os.path.join(project_root, "input"))
    parser.add_argument("--output-dir", default=os.path.join(project_root, "output"))
    parser.add_argument("--fetch-timeout-seconds", type=int, default=600)
    parser.add_argument("--poll-interval-seconds", type=int, default=5)
    return parser.parse_args(argv)


def _failure_summary(
    output_path: str,
    baseline_manifest: str,
    errors: Sequence[str],
) -> None:
    _write_summary(
        output_path,
        render_summary(
            status="FAIL",
            baseline_manifest=baseline_manifest,
            live_manifest="N/A",
            live_report="N/A",
            mapping_document="N/A",
            deltas=_empty_deltas(),
            errors=errors,
        ),
    )


def run(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.abspath(args.output_dir)
    input_dir = os.path.abspath(args.input_dir)
    top_summary_path = os.path.join(output_dir, f"Final_Acceptance_Summary_{args.year}.md")

    try:
        baseline_manifest_path = _latest_manifest_path(output_dir)
        baseline_manifest = _load_json(baseline_manifest_path)
    except Exception as exc:
        print(f"FINAL_ACCEPTANCE status=FAIL reason=baseline_unavailable detail={exc}")
        return 2

    baseline_errors = _validate_baseline_manifest(baseline_manifest, args.year)
    if baseline_errors:
        _failure_summary(top_summary_path, baseline_manifest_path, baseline_errors)
        print("FINAL_ACCEPTANCE status=FAIL reason=invalid_offline_baseline")
        print(f"FINAL_ACCEPTANCE_SUMMARY: {top_summary_path}")
        return 2

    baseline_report_path = os.path.abspath(baseline_manifest["report_path"])
    try:
        baseline_parsed = parse_report(_read_text(baseline_report_path))
        baseline_report_errors = validate_report(baseline_parsed)
    except Exception as exc:
        baseline_report_errors = [f"baseline report could not be parsed: {exc}"]
        baseline_parsed = None
    if baseline_report_errors:
        _failure_summary(top_summary_path, baseline_manifest_path, baseline_report_errors)
        print("FINAL_ACCEPTANCE status=FAIL reason=invalid_offline_report")
        print(f"FINAL_ACCEPTANCE_SUMMARY: {top_summary_path}")
        return 2

    command = [
        sys.executable,
        os.path.join(script_dir, "iepms_guarded_runner.py"),
        "--fetch",
        "--year",
        str(args.year),
        "--force-convert",
        "--input-dir",
        input_dir,
        "--output-dir",
        output_dir,
        "--fetch-timeout-seconds",
        str(args.fetch_timeout_seconds),
        "--poll-interval-seconds",
        str(args.poll_interval_seconds),
    ]

    print("\n=== FINAL ACCEPTANCE: GUARDED LIVE FETCH ===")
    result = _run_live_command(command, script_dir)
    combined_output = (result.stdout or "") + "\n" + (result.stderr or "")
    errors: List[str] = []
    if result.returncode != 0:
        errors.append(f"guarded live runner exited with code {result.returncode}")
    for marker in REQUIRED_MARKERS:
        if marker not in combined_output:
            errors.append(f"guarded live output is missing marker: {marker}")

    try:
        live_manifest_path = _latest_manifest_path(output_dir)
        live_manifest = _load_json(live_manifest_path)
    except Exception as exc:
        errors.append(f"live manifest could not be loaded: {exc}")
        live_manifest_path = "N/A"
        live_manifest = {}

    if live_manifest_path == baseline_manifest_path:
        errors.append("live run did not replace the baseline latest manifest")
    errors.extend(_validate_live_manifest(live_manifest, args.year))

    live_report_path = live_manifest.get("report_path") or "N/A"
    live_run_dir = (
        os.path.dirname(os.path.abspath(live_manifest_path))
        if live_manifest_path != "N/A"
        else output_dir
    )
    mapping_path = os.path.join(live_run_dir, "milestone_mappings.md")

    live_parsed = None
    if live_report_path != "N/A" and os.path.isfile(live_report_path):
        try:
            live_parsed = parse_report(_read_text(live_report_path))
            errors.extend(validate_report(live_parsed))
        except Exception as exc:
            errors.append(f"live report could not be parsed: {exc}")
    if os.path.isfile(mapping_path):
        try:
            errors.extend(validate_mapping_document(_read_text(mapping_path)))
        except Exception as exc:
            errors.append(f"mapping document could not be parsed: {exc}")
    else:
        errors.append("live mapping document is missing")

    deltas = _empty_deltas()
    if baseline_parsed is not None and live_parsed is not None:
        try:
            deltas = compare_reports(baseline_parsed, live_parsed)
        except Exception as exc:
            errors.append(f"baseline/live comparison failed: {exc}")

    status = "PASS" if not errors else "FAIL"
    summary = render_summary(
        status=status,
        baseline_manifest=baseline_manifest_path,
        live_manifest=live_manifest_path,
        live_report=os.path.abspath(live_report_path) if live_report_path != "N/A" else "N/A",
        mapping_document=os.path.abspath(mapping_path) if os.path.isfile(mapping_path) else "N/A",
        deltas=deltas,
        errors=errors,
    )
    run_summary_path = os.path.join(live_run_dir, f"Final_Acceptance_Summary_{args.year}.md")
    _write_summary(run_summary_path, summary)
    os.makedirs(output_dir, exist_ok=True)
    shutil.copyfile(run_summary_path, top_summary_path)

    print(f"\nFINAL_ACCEPTANCE status={status}")
    print(f"BASELINE_MANIFEST: {baseline_manifest_path}")
    print(f"LIVE_MANIFEST: {live_manifest_path}")
    print(f"LIVE_REPORT: {live_report_path}")
    print(f"MAPPING_DOCUMENT: {mapping_path if os.path.isfile(mapping_path) else 'N/A'}")
    print(f"FINAL_ACCEPTANCE_SUMMARY: {run_summary_path}")
    print(
        "KEY_DELTA "
        f"TX_Mini_Project_RFS={_signed(deltas['models']['TX Mini Project']['RFS'])} "
        f"ZTE_TX_MINI_RFS={_signed(deltas['models']['ZTE TX MINI']['RFS'])}"
    )
    if errors:
        for error in errors:
            print(f"ACCEPTANCE_ERROR: {error}")
        return 2
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
