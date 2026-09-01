import os
import unittest
from unittest.mock import patch

from scripts import iepms_guarded_runner


class GuardedRunnerTests(unittest.TestCase):
    def test_injects_guarded_analyzer_and_requires_all_live_mappings(self):
        captured = {}

        def fake_run(argv):
            captured["argv"] = list(argv)
            captured["require_all"] = os.environ.get("IEPMS_GUARD_REQUIRE_ALL")
            return 0

        with patch.object(iepms_guarded_runner.iepms_safe_runner, "run", side_effect=fake_run):
            result = iepms_guarded_runner.run(["--fetch", "--year", "2026"])

        self.assertEqual(result, 0)
        self.assertEqual(captured["require_all"], "1")
        analyzer_index = captured["argv"].index("--analyzer-script") + 1
        self.assertTrue(captured["argv"][analyzer_index].endswith("guarded_analyzer.py"))

    def test_replaces_any_caller_supplied_analyzer_script(self):
        captured = {}

        def fake_run(argv):
            captured["argv"] = list(argv)
            return 0

        with patch.object(iepms_guarded_runner.iepms_safe_runner, "run", side_effect=fake_run):
            iepms_guarded_runner.run(
                ["--offline", "--analyzer-script", "unsafe.py", "--year", "2026"]
            )

        self.assertNotIn("unsafe.py", captured["argv"])
        self.assertEqual(captured["argv"].count("--analyzer-script"), 1)


if __name__ == "__main__":
    unittest.main()
