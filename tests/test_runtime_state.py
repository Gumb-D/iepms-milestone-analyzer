import argparse
import io
import os
import unittest
from contextlib import redirect_stdout

from scripts.runtime_state import PollWindow, emit_run_state, positive_int


class FakeClock:
    def __init__(self):
        self.now = 100.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class RuntimeStateTests(unittest.TestCase):
    def test_positive_int_accepts_positive_values(self):
        self.assertEqual(positive_int("600"), 600)
        self.assertEqual(positive_int("5"), 5)

    def test_positive_int_rejects_zero_negative_and_non_numeric_values(self):
        for value in ("0", "-1", "abc"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    positive_int(value)

    def test_emit_run_state_uses_stable_machine_readable_format(self):
        output = io.StringIO()
        with redirect_stdout(output):
            line = emit_run_state(
                "POLLING",
                elapsed_seconds=125,
                remaining_seconds=475,
                pending_count=1,
                pending="2023_TX_Rollout",
            )

        expected = (
            "RUN_STATE stage=POLLING elapsed_seconds=125 remaining_seconds=475 "
            "pending_count=1 pending=2023_TX_Rollout"
        )
        self.assertEqual(line, expected)
        self.assertEqual(output.getvalue(), expected + "\n")

    def test_poll_window_tracks_elapsed_remaining_and_pending_names(self):
        clock = FakeClock()
        window = PollWindow(
            timeout_seconds=10,
            interval_seconds=4,
            monotonic=clock.monotonic,
            sleeper=clock.sleep,
        )

        first = window.snapshot(["B", "A"])
        self.assertEqual(first["elapsed_seconds"], 0)
        self.assertEqual(first["remaining_seconds"], 10)
        self.assertEqual(first["pending_count"], 2)
        self.assertEqual(first["pending"], "A,B")

        slept = window.sleep()
        self.assertEqual(slept, 4)
        self.assertEqual(clock.sleeps, [4])

        second = window.snapshot(["A"])
        self.assertEqual(second["elapsed_seconds"], 4)
        self.assertEqual(second["remaining_seconds"], 6)
        self.assertFalse(window.expired())

    def test_poll_window_sleeps_only_until_deadline_and_expires_by_time(self):
        clock = FakeClock()
        window = PollWindow(
            timeout_seconds=5,
            interval_seconds=4,
            monotonic=clock.monotonic,
            sleeper=clock.sleep,
        )

        self.assertEqual(window.sleep(), 4)
        self.assertEqual(window.sleep(), 1)
        self.assertTrue(window.expired())
        self.assertEqual(window.sleep(), 0)
        self.assertEqual(clock.sleeps, [4, 1])

    def test_legacy_analyzer_no_longer_uses_fixed_max_poll_count(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        analyzer_path = os.path.join(project_root, "scripts", "IEPMS_Milestone_Analyzer.py")
        with open(analyzer_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertNotIn("max_polls = 24", source)
        self.assertIn("--fetch-timeout-seconds", source)
        self.assertIn("--poll-interval-seconds", source)
        self.assertIn("PollWindow", source)


if __name__ == "__main__":
    unittest.main()
