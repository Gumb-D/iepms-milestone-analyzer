import csv
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from scripts import guarded_analyzer


class GuardedAnalyzerTests(unittest.TestCase):
    def _write_tx_mini_csv(self, input_dir, include_actual_end=True):
        width = 260
        headers = [["" for _ in range(width)] for _ in range(4)]

        milestone_columns = {
            "SOW": (250, "TX Planning", "TX Planning"),
            "TSS": (70, "Survey&Design", "Physical Survey"),
            "MC": (96, "Ready For Installation", "Material Collection"),
            "MOS": (101, "Material On Site", "Material On Site"),
            "TI": (107, "Telecom Installation", "Equipment Installation"),
            "L1": (128, "Q&EHS", "L1 Approved"),
            "PAC": (222, "Acceptance Certification", "PAC Approved"),
        }
        for milestone, (index, stage, task) in milestone_columns.items():
            headers[0][index] = f"{milestone}|actual_end_date"
            headers[1][index] = stage
            headers[2][index] = task
            headers[3][index] = "actual end time"

        headers[0][119] = "WP11400|AC0000111569|planned_end_date"
        headers[1][119] = "Software Commissioning"
        headers[2][119] = "TX Integrated"
        headers[3][119] = "planned end time"

        if include_actual_end:
            headers[0][121] = "WP11400|AC0000111569|actual_end_date"
            headers[1][121] = "Software Commissioning"
            headers[2][121] = "TX Integrated"
            headers[3][121] = "actual end time"

        path = os.path.join(input_dir, "TX_Mini_Project.csv")
        with open(path, "w", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerows(headers)
        return path

    def test_writes_rebound_config_before_launching_legacy_analyzer(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = os.path.join(tmp, "input")
            output_dir = os.path.join(tmp, "output")
            docs_dir = os.path.join(tmp, "docs")
            os.makedirs(input_dir)
            self._write_tx_mini_csv(input_dir)

            captured = {}

            def fake_stream(command, cwd):
                captured["command"] = command
                captured["cwd"] = cwd
                return 0

            with patch.object(guarded_analyzer, "_stream", side_effect=fake_stream):
                result = guarded_analyzer.run([
                    "--year", "2026",
                    "--input-dir", input_dir,
                    "--output-dir", output_dir,
                    "--docs-dir", docs_dir,
                    "--no-convert",
                ])

            self.assertEqual(result, 0)
            config_index = captured["command"].index("--config") + 1
            config_path = captured["command"][config_index]
            with open(config_path, encoding="utf-8") as handle:
                resolved = json.load(handle)
            self.assertEqual(resolved["TX_Mini_Project.csv"]["RFS"], 121)
            self.assertIn("--no-convert", captured["command"])

    def test_does_not_launch_legacy_analyzer_when_actual_end_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = os.path.join(tmp, "input")
            output_dir = os.path.join(tmp, "output")
            docs_dir = os.path.join(tmp, "docs")
            os.makedirs(input_dir)
            self._write_tx_mini_csv(input_dir, include_actual_end=False)

            with patch.object(guarded_analyzer, "_stream") as mocked_stream:
                result = guarded_analyzer.run([
                    "--year", "2026",
                    "--input-dir", input_dir,
                    "--output-dir", output_dir,
                    "--docs-dir", docs_dir,
                    "--no-convert",
                ])

            self.assertEqual(result, 2)
            mocked_stream.assert_not_called()


if __name__ == "__main__":
    unittest.main()
