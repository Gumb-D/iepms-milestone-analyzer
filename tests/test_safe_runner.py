import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import iepms_safe_runner


class SafeRunnerTests(unittest.TestCase):
    def _fake_completed_process(self, command, returncode=0, stdout="ANALYSIS COMPLETE!\n", stderr=""):
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)

    def test_parser_rejects_missing_mode(self):
        with self.assertRaises(SystemExit):
            iepms_safe_runner.parse_args([])

    def test_live_fetch_fails_closed_when_any_expected_file_is_not_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = os.path.join(tmp, "input")
            output_dir = os.path.join(tmp, "output")
            docs_dir = os.path.join(tmp, "docs")
            os.makedirs(input_dir)

            def fake_run(command, **kwargs):
                output_index = command.index("--output-dir") + 1
                working_output = command[output_index]
                os.makedirs(working_output, exist_ok=True)
                report = os.path.join(working_output, "Milestone_Progress_Report_2026.md")
                with open(report, "w", encoding="utf-8") as handle:
                    handle.write("stale-looking report")
                first = iepms_safe_runner.EXPECTED_EXPORTS[0]
                with open(os.path.join(input_dir, first + ".xlsx"), "wb") as handle:
                    handle.write(b"fresh")
                return self._fake_completed_process(command)

            with patch.object(iepms_safe_runner.subprocess, "run", side_effect=fake_run):
                rc = iepms_safe_runner.run([
                    "--fetch",
                    "--year", "2026",
                    "--input-dir", input_dir,
                    "--output-dir", output_dir,
                    "--docs-dir", docs_dir,
                ])

            self.assertNotEqual(rc, 0)
            self.assertFalse(os.path.exists(os.path.join(output_dir, "latest.json")))
            manifests = []
            for root, _, files in os.walk(os.path.join(output_dir, "runs")):
                if "manifest.json" in files:
                    manifests.append(os.path.join(root, "manifest.json"))
                self.assertNotIn("Milestone_Progress_Report_2026.md", files)
            self.assertEqual(len(manifests), 1)
            with open(manifests[0], encoding="utf-8") as handle:
                manifest = json.load(handle)
            self.assertEqual(manifest["status"], "FAILED")
            self.assertEqual(manifest["downloaded_files"], [iepms_safe_runner.EXPECTED_EXPORTS[0]])
            self.assertGreater(len(manifest["missing_files"]), 0)

    def test_offline_success_publishes_verified_manifest_and_latest_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = os.path.join(tmp, "input")
            output_dir = os.path.join(tmp, "output")
            docs_dir = os.path.join(tmp, "docs")
            os.makedirs(input_dir)

            def fake_run(command, **kwargs):
                output_index = command.index("--output-dir") + 1
                working_output = command[output_index]
                docs_index = command.index("--docs-dir") + 1
                working_docs = command[docs_index]
                os.makedirs(working_output, exist_ok=True)
                os.makedirs(working_docs, exist_ok=True)
                with open(os.path.join(working_output, "Milestone_Progress_Report_2026.md"), "w", encoding="utf-8") as handle:
                    handle.write("verified offline report")
                with open(os.path.join(working_docs, "milestone_mappings.md"), "w", encoding="utf-8") as handle:
                    handle.write("mapping")
                return self._fake_completed_process(command)

            with patch.object(iepms_safe_runner.subprocess, "run", side_effect=fake_run):
                rc = iepms_safe_runner.run([
                    "--offline",
                    "--year", "2026",
                    "--input-dir", input_dir,
                    "--output-dir", output_dir,
                    "--docs-dir", docs_dir,
                ])

            self.assertEqual(rc, 0)
            with open(os.path.join(output_dir, "latest.json"), encoding="utf-8") as handle:
                pointer = json.load(handle)
            with open(pointer["manifest_path"], encoding="utf-8") as handle:
                manifest = json.load(handle)
            self.assertEqual(manifest["status"], "SUCCESS")
            self.assertEqual(manifest["mode"], "OFFLINE_LOCAL")
            self.assertEqual(manifest["source"], "LOCAL_INPUT")
            self.assertTrue(os.path.exists(manifest["report_path"]))

    def test_live_success_requires_all_six_fresh_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = os.path.join(tmp, "input")
            output_dir = os.path.join(tmp, "output")
            docs_dir = os.path.join(tmp, "docs")
            os.makedirs(input_dir)

            def fake_run(command, **kwargs):
                output_index = command.index("--output-dir") + 1
                working_output = command[output_index]
                docs_index = command.index("--docs-dir") + 1
                working_docs = command[docs_index]
                os.makedirs(working_output, exist_ok=True)
                os.makedirs(working_docs, exist_ok=True)
                for clean_name in iepms_safe_runner.EXPECTED_EXPORTS:
                    with open(os.path.join(input_dir, clean_name + ".xlsx"), "wb") as handle:
                        handle.write(b"fresh")
                with open(os.path.join(working_output, "Milestone_Progress_Report_2026.md"), "w", encoding="utf-8") as handle:
                    handle.write("verified live report")
                return self._fake_completed_process(command)

            with patch.object(iepms_safe_runner.subprocess, "run", side_effect=fake_run):
                rc = iepms_safe_runner.run([
                    "--fetch",
                    "--year", "2026",
                    "--input-dir", input_dir,
                    "--output-dir", output_dir,
                    "--docs-dir", docs_dir,
                ])

            self.assertEqual(rc, 0)
            with open(os.path.join(output_dir, "latest.json"), encoding="utf-8") as handle:
                pointer = json.load(handle)
            with open(pointer["manifest_path"], encoding="utf-8") as handle:
                manifest = json.load(handle)
            self.assertEqual(manifest["expected_files"], iepms_safe_runner.EXPECTED_EXPORTS)
            self.assertEqual(manifest["downloaded_files"], iepms_safe_runner.EXPECTED_EXPORTS)
            self.assertEqual(manifest["mode"], "LIVE_FETCH")
            self.assertEqual(manifest["source"], "ZTE_IEPMS_API")


if __name__ == "__main__":
    unittest.main()
