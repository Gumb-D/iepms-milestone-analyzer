import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import iepms_safe_runner


class SafeRunnerRuntimeTests(unittest.TestCase):
    def _completed(self, command, stdout="ANALYSIS COMPLETE!\n"):
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    def test_parser_uses_runtime_defaults_and_accepts_overrides(self):
        defaults = iepms_safe_runner.parse_args(["--fetch"])
        self.assertEqual(defaults.fetch_timeout_seconds, 600)
        self.assertEqual(defaults.poll_interval_seconds, 5)

        custom = iepms_safe_runner.parse_args(
            [
                "--fetch",
                "--fetch-timeout-seconds", "900",
                "--poll-interval-seconds", "10",
            ]
        )
        self.assertEqual(custom.fetch_timeout_seconds, 900)
        self.assertEqual(custom.poll_interval_seconds, 10)

    def test_parser_rejects_non_positive_runtime_values(self):
        for option, value in (
            ("--fetch-timeout-seconds", "0"),
            ("--poll-interval-seconds", "-1"),
        ):
            with self.subTest(option=option, value=value):
                with self.assertRaises(SystemExit):
                    iepms_safe_runner.parse_args(["--fetch", option, value])

    def test_live_runner_fetches_with_runtime_options_then_analyzes_without_legacy_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = os.path.join(tmp, "input")
            output_dir = os.path.join(tmp, "output")
            docs_dir = os.path.join(tmp, "docs")
            os.makedirs(input_dir)
            seen_command = []

            def fake_fetch(script_dir, selected_input, **kwargs):
                self.assertEqual(selected_input, input_dir)
                self.assertEqual(kwargs["fetch_timeout_seconds"], 900)
                self.assertEqual(kwargs["poll_interval_seconds"], 10)
                for clean_name in iepms_safe_runner.EXPECTED_EXPORTS:
                    with open(os.path.join(input_dir, clean_name + ".xlsx"), "wb") as handle:
                        handle.write(b"fresh xlsx")
                return True

            def fake_analyzer(command, cwd):
                seen_command.extend(command)
                working_output = command[command.index("--output-dir") + 1]
                os.makedirs(working_output, exist_ok=True)
                for clean_name in iepms_safe_runner.EXPECTED_EXPORTS:
                    with open(os.path.join(input_dir, clean_name + ".csv"), "w", encoding="utf-8") as handle:
                        handle.write("fresh csv")
                report = os.path.join(working_output, "Milestone_Progress_Report_2026.md")
                with open(report, "w", encoding="utf-8") as handle:
                    handle.write("\n".join(
                        f"#### DU Model: {model}"
                        for model in iepms_safe_runner.EXPECTED_REPORT_MODELS
                    ))
                return self._completed(command, stdout="Loading milestone mapping configuration\nANALYSIS COMPLETE!\n")

            with patch.object(iepms_safe_runner, "fetch_latest_exports", side_effect=fake_fetch):
                with patch.object(iepms_safe_runner, "_run_analyzer", side_effect=fake_analyzer):
                    rc = iepms_safe_runner.run(
                        [
                            "--fetch",
                            "--year", "2026",
                            "--fetch-timeout-seconds", "900",
                            "--poll-interval-seconds", "10",
                            "--input-dir", input_dir,
                            "--output-dir", output_dir,
                            "--docs-dir", docs_dir,
                        ]
                    )

            self.assertEqual(rc, 0)
            self.assertNotIn("--fetch", seen_command)
            with open(os.path.join(output_dir, "latest.json"), encoding="utf-8") as handle:
                pointer = json.load(handle)
            with open(pointer["manifest_path"], encoding="utf-8") as handle:
                manifest = json.load(handle)

            self.assertEqual(manifest["schema_version"], 2)
            self.assertEqual(
                manifest["runtime"],
                {"fetch_timeout_seconds": 900, "poll_interval_seconds": 10},
            )
            for key in (
                "total_seconds",
                "fetch_seconds",
                "analyzer_seconds",
                "verification_seconds",
            ):
                self.assertIn(key, manifest["timings"])
                self.assertGreaterEqual(manifest["timings"][key], 0)

    def test_exact_legacy_converter_error_fails_closed_and_records_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = os.path.join(tmp, "input")
            output_dir = os.path.join(tmp, "output")
            docs_dir = os.path.join(tmp, "docs")
            os.makedirs(input_dir)

            def fake_analyzer(command, cwd):
                working_output = command[command.index("--output-dir") + 1]
                os.makedirs(working_output, exist_ok=True)
                report = os.path.join(working_output, "Milestone_Progress_Report_2026.md")
                with open(report, "w", encoding="utf-8") as handle:
                    handle.write("partial report")
                return self._completed(
                    command,
                    stdout=(
                        "Failed to convert MW_EOS_Swap.xlsx: broken workbook\n"
                        "ANALYSIS COMPLETE!\n"
                    ),
                )

            with patch.object(iepms_safe_runner, "_run_analyzer", side_effect=fake_analyzer):
                rc = iepms_safe_runner.run(
                    [
                        "--offline",
                        "--year", "2026",
                        "--input-dir", input_dir,
                        "--output-dir", output_dir,
                        "--docs-dir", docs_dir,
                    ]
                )

            self.assertEqual(rc, 2)
            self.assertFalse(os.path.exists(os.path.join(output_dir, "latest.json")))
            manifests = []
            for root, _, files in os.walk(os.path.join(output_dir, "runs")):
                if "manifest.json" in files:
                    manifests.append(os.path.join(root, "manifest.json"))
            self.assertEqual(len(manifests), 1)
            with open(manifests[0], encoding="utf-8") as handle:
                manifest = json.load(handle)
            self.assertEqual(manifest["status"], "FAILED")
            self.assertIn("Failed to convert", manifest["error"])
            self.assertIn("timings", manifest)
            self.assertIn("runtime", manifest)


if __name__ == "__main__":
    unittest.main()
