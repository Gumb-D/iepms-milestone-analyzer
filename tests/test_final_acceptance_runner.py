import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import final_acceptance_runner


MILESTONES = ("SOW", "TSS", "MC", "MOS", "TI", "L1", "RFS", "PAC")
MODELS = (
    "2023 TX Rollout",
    "2024 Celcomdigi BAU",
    "Jendela TX Migration",
    "TX Mini Project",
    "MW EOS Swap",
    "ZTE TX MINI",
)
EXPECTED_EXPORTS = tuple(model.replace(" ", "_") for model in MODELS)


def _progress_table(counts):
    lines = [
        "| Milestone | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | **Total** |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for milestone in MILESTONES:
        total = counts[milestone]
        months = [total] + [0] * 11
        lines.append(
            f"| **{milestone}** | "
            + " | ".join(str(value) for value in months)
            + f" | **{sum(months)}** |"
        )
    return "\n".join(lines)


def _sla_table(open_by_model):
    lines = [
        "| DU Model | Open Backlog | Within SLA | Warning | Critical (Breached) | Compliance % | Avg Days Open |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    total = 0
    for model in MODELS:
        count = open_by_model[model]
        total += count
        lines.append(f"| {model} | {count} | {count} | 0 | 0 | **100.0%** | 1.0 |")
    lines.append(f"| **Total** | **{total}** | **{total}** | **0** | **0** | **100.0%** | **1.0** |")
    return "\n".join(lines)


def build_report(tx_mini_rfs_extra=0):
    model_counts = {
        model: {milestone: 1 for milestone in MILESTONES}
        for model in MODELS
    }
    model_counts["TX Mini Project"]["RFS"] += tx_mini_rfs_extra
    combined = {
        milestone: sum(model_counts[model][milestone] for model in MODELS)
        for milestone in MILESTONES
    }
    lines = [
        "# Milestone Progress Report - Year 2026",
        "",
        "## 1. Combined Monthly Progress (All Projects)",
        "",
        _progress_table(combined),
        "",
        "## 2. Progress Breakdown by Project & DU Model",
        "",
        "### Project: Malaysia CelcomDigi Project",
        "",
    ]
    for model in MODELS[:4]:
        lines.extend([f"#### DU Model: {model}", "", _progress_table(model_counts[model]), ""])
    lines.extend(["### Project: CelcomDigi MW", ""])
    for model in MODELS[4:]:
        lines.extend([f"#### DU Model: {model}", "", _progress_table(model_counts[model]), ""])
    open_by_model = {model: 1 for model in MODELS}
    lines.extend(
        [
            "## 3. SLA & KPI Performance",
            "",
            "### 3.1 MC ➔ MOS SLA Backlog (Year 2026 Only)",
            "",
            _sla_table(open_by_model),
            "",
            "### 3.2 TI ➔ L1 SLA Backlog (Year 2026 Only)",
            "",
            _sla_table(open_by_model),
            "",
            "### 3.3 MC ➔ PAC SLA Backlog (Year 2026 Only)",
            "",
            _sla_table(open_by_model),
            "",
        ]
    )
    return "\n".join(lines)


VALID_MAPPING_DOCUMENT = """# Project Milestone vs Column Header Mappings

## TX Mini Project

| Milestone | Col Index | Row 0 (ID/Code) | Row 1 (WBS Stage) | Row 2 (Task Name) | Row 3 (Display Header) |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **RFS** | 127 | `WP11400|AC0000111569|actual_end_date` | Software Commissioning | TX Integrated | `actual end time` |

## ZTE TX MINI

| Milestone | Col Index | Row 0 (ID/Code) | Row 1 (WBS Stage) | Row 2 (Task Name) | Row 3 (Display Header) |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **TSS** | 45 | `WP10400|AC0000197581|actual_end_date` | Survey&Design | Physical Survey | `actual end time` |
| **L1** | 133 | `WPC000013474|AC0000197764|actual_end_date` | Q&EHS | L1 Approved | `actual end time` |
| **RFS** | 124 | `WP11400|AC0000197593|actual_end_date` | Software Commissioning | Site Integrated | `actual end time` |
"""


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def _seed_run(output_dir, run_id, mode, report_text, mapping_text=VALID_MAPPING_DOCUMENT):
    run_dir = os.path.join(output_dir, "runs", run_id)
    os.makedirs(run_dir, exist_ok=True)
    report_path = os.path.join(run_dir, "Milestone_Progress_Report_2026.md")
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(report_text)
    mapping_path = os.path.join(run_dir, "milestone_mappings.md")
    with open(mapping_path, "w", encoding="utf-8") as handle:
        handle.write(mapping_text)
    manifest_path = os.path.join(run_dir, "manifest.json")
    live = mode == "LIVE_FETCH"
    _write_json(
        manifest_path,
        {
            "schema_version": 2,
            "run_id": run_id,
            "status": "SUCCESS",
            "mode": mode,
            "target_year": 2026,
            "expected_files": list(EXPECTED_EXPORTS) if live else [],
            "downloaded_files": list(EXPECTED_EXPORTS) if live else [],
            "missing_files": [],
            "report_path": report_path,
            "source": "ZTE_IEPMS_API" if live else "LOCAL_INPUT",
            "error": None,
        },
    )
    _write_json(os.path.join(output_dir, "latest.json"), {"manifest_path": manifest_path})
    return manifest_path, report_path, mapping_path


class FinalAcceptanceRunnerTests(unittest.TestCase):
    def test_parses_combined_du_and_sla_tables(self):
        parsed = final_acceptance_runner.parse_report(build_report())

        self.assertEqual(parsed["combined"]["RFS"]["total"], 6)
        self.assertEqual(parsed["models"]["TX Mini Project"]["RFS"]["total"], 1)
        self.assertEqual(parsed["sla"]["TI_L1"]["Combined"]["open"], 6)

    def test_validation_rejects_combined_total_not_equal_to_models(self):
        parsed = final_acceptance_runner.parse_report(build_report())
        parsed["combined"]["RFS"]["total"] = 7

        errors = final_acceptance_runner.validate_report(parsed, MODELS)

        self.assertTrue(any("combined RFS" in error for error in errors))

    def test_compare_reports_returns_tx_mini_deltas(self):
        baseline = final_acceptance_runner.parse_report(build_report())
        live = final_acceptance_runner.parse_report(build_report(tx_mini_rfs_extra=1))

        delta = final_acceptance_runner.compare_reports(baseline, live)

        self.assertEqual(delta["combined"]["RFS"], 1)
        self.assertEqual(delta["models"]["TX Mini Project"]["RFS"], 1)

    def test_mapping_validation_requires_exact_tx_mini_identities(self):
        self.assertEqual(final_acceptance_runner.validate_mapping_document(VALID_MAPPING_DOCUMENT), [])

        invalid = VALID_MAPPING_DOCUMENT.replace("Site Integrated", "Cut-over End Date")
        errors = final_acceptance_runner.validate_mapping_document(invalid)

        self.assertTrue(any("ZTE TX MINI RFS" in error for error in errors))

    def test_summary_contains_paths_status_and_key_deltas(self):
        deltas = final_acceptance_runner.compare_reports(
            final_acceptance_runner.parse_report(build_report()),
            final_acceptance_runner.parse_report(build_report(tx_mini_rfs_extra=1)),
        )

        text = final_acceptance_runner.render_summary(
            status="PASS",
            baseline_manifest="baseline/manifest.json",
            live_manifest="live/manifest.json",
            live_report="live/report.md",
            mapping_document="live/milestone_mappings.md",
            deltas=deltas,
            errors=[],
        )

        self.assertIn("# Final Acceptance Summary - PASS", text)
        self.assertIn("TX Mini Project", text)
        self.assertIn("ZTE TX MINI", text)
        self.assertIn("baseline/manifest.json", text)

    def test_run_executes_guarded_live_fetch_and_writes_pass_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = os.path.join(tmp, "output")
            input_dir = os.path.join(tmp, "input")
            os.makedirs(input_dir)
            _seed_run(output_dir, "offline", "OFFLINE_LOCAL", build_report())
            captured = {}

            def fake_live(command, cwd):
                captured["command"] = list(command)
                _seed_run(
                    output_dir,
                    "live",
                    "LIVE_FETCH",
                    build_report(tx_mini_rfs_extra=1),
                )
                output = "\n".join(
                    [
                        "MAPPING_VALIDATION_COMPLETE files=6 rebound=0 config=x",
                        "RUN_STATE stage=SUCCESS run_id=live mode=LIVE_FETCH",
                        "VERIFIED ANALYSIS COMPLETE!",
                    ]
                )
                return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

            with patch.object(final_acceptance_runner, "_run_live_command", side_effect=fake_live):
                result = final_acceptance_runner.run(
                    ["--year", "2026", "--input-dir", input_dir, "--output-dir", output_dir]
                )

            self.assertEqual(result, 0)
            self.assertIn("--fetch", captured["command"])
            self.assertIn("--force-convert", captured["command"])
            self.assertTrue(
                os.path.isfile(os.path.join(output_dir, "Final_Acceptance_Summary_2026.md"))
            )
            self.assertTrue(
                os.path.isfile(
                    os.path.join(output_dir, "runs", "live", "Final_Acceptance_Summary_2026.md")
                )
            )

    def test_run_fails_closed_when_baseline_is_not_successful_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = os.path.join(tmp, "output")
            input_dir = os.path.join(tmp, "input")
            os.makedirs(input_dir)
            _seed_run(output_dir, "wrong-baseline", "LIVE_FETCH", build_report())

            with patch.object(final_acceptance_runner, "_run_live_command") as mocked:
                result = final_acceptance_runner.run(
                    ["--year", "2026", "--input-dir", input_dir, "--output-dir", output_dir]
                )

            self.assertEqual(result, 2)
            mocked.assert_not_called()

    def test_run_fails_when_guarded_output_lacks_mapping_complete_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = os.path.join(tmp, "output")
            input_dir = os.path.join(tmp, "input")
            os.makedirs(input_dir)
            _seed_run(output_dir, "offline", "OFFLINE_LOCAL", build_report())

            def fake_live(command, cwd):
                _seed_run(output_dir, "live", "LIVE_FETCH", build_report())
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout="RUN_STATE stage=SUCCESS\nVERIFIED ANALYSIS COMPLETE!",
                    stderr="",
                )

            with patch.object(final_acceptance_runner, "_run_live_command", side_effect=fake_live):
                result = final_acceptance_runner.run(
                    ["--year", "2026", "--input-dir", input_dir, "--output-dir", output_dir]
                )

            self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
