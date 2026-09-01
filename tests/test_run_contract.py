import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from scripts.run_contract import (
    LIVE_FETCH,
    create_run_context,
    update_latest_pointer,
    verify_downloaded_files,
    write_manifest,
)


class RunContractTests(unittest.TestCase):
    def test_verify_downloaded_files_requires_fresh_non_empty_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            started = 1_700_000_000.0
            fresh = os.path.join(tmp, "Fresh.xlsx")
            stale = os.path.join(tmp, "Stale.xlsx")
            empty = os.path.join(tmp, "Empty.xlsx")
            with open(fresh, "wb") as handle:
                handle.write(b"data")
            with open(stale, "wb") as handle:
                handle.write(b"old")
            open(empty, "wb").close()
            os.utime(fresh, (started + 1, started + 1))
            os.utime(stale, (started - 10, started - 10))
            os.utime(empty, (started + 1, started + 1))

            downloaded, missing = verify_downloaded_files(
                tmp, ["Fresh", "Stale", "Empty", "Absent"], started
            )

            self.assertEqual(downloaded, ["Fresh"])
            self.assertEqual(missing, ["Stale", "Empty", "Absent"])

    def test_accepts_file_created_in_same_coarse_timestamp_second(self):
        with tempfile.TemporaryDirectory() as tmp:
            started = 1_700_000_000.750
            path = os.path.join(tmp, "Fresh.xlsx")
            with open(path, "wb") as handle:
                handle.write(b"data")

            # Some Windows/filesystem combinations expose write timestamps only to
            # whole-second precision even though the run start time has fractions.
            os.utime(path, (1_700_000_000.0, 1_700_000_000.0))

            downloaded, missing = verify_downloaded_files(
                tmp, ["Fresh"], started
            )

            self.assertEqual(downloaded, ["Fresh"])
            self.assertEqual(missing, [])

    def test_failed_manifest_preserves_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = datetime(2026, 7, 14, 10, 15, 30, tzinfo=timezone(timedelta(hours=8)))
            context = create_run_context(tmp, 2026, LIVE_FETCH, now=now)

            manifest_path = write_manifest(
                context,
                status="FAILED",
                expected_files=["A", "B"],
                downloaded_files=["A"],
                missing_files=["B"],
                source="ZTE_IEPMS_API",
                error="Incomplete live fetch",
            )

            with open(manifest_path, encoding="utf-8") as handle:
                manifest = json.load(handle)
            self.assertEqual(manifest["status"], "FAILED")
            self.assertEqual(manifest["missing_files"], ["B"])
            self.assertEqual(manifest["error"], "Incomplete live fetch")
            self.assertIsNone(manifest["report_path"])

    def test_latest_pointer_is_written_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = os.path.join(tmp, "runs", "run-1", "manifest.json")
            os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
            with open(manifest_path, "w", encoding="utf-8") as handle:
                handle.write("{}")

            pointer_path = update_latest_pointer(tmp, manifest_path)

            with open(pointer_path, encoding="utf-8") as handle:
                pointer = json.load(handle)
            self.assertEqual(pointer["manifest_path"], manifest_path)
            self.assertFalse(os.path.exists(pointer_path + ".tmp"))


if __name__ == "__main__":
    unittest.main()
