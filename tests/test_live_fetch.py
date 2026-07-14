import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from scripts import live_fetch


class FakeClock:
    def __init__(self):
        self.now = 10.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class FakeResponse:
    def __init__(self, payload=None, content=b"export", status_code=200):
        self._payload = payload or {}
        self._content = content
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=8192):
        yield self._content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class PendingRequests:
    def get(self, url, **kwargs):
        return FakeResponse({"bo": {"rows": []}})


class TrackingPendingRequests:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse({"bo": {"rows": []}})


class ReadyRequests:
    def __init__(self):
        self.calls = 0

    def get(self, url, **kwargs):
        if "download" in url:
            return FakeResponse(content=b"fresh export")
        self.calls += 1
        return FakeResponse(
            {
                "bo": {
                    "rows": [
                        {
                            "fileName": "2023 TX Rollout export.xlsx",
                            "submitDate": "2026-07-14 11:00:00",
                            "status": "SUCCESS",
                            "schedule": 100,
                            "operationNo": "EX001",
                            "fileId": "file-1",
                        }
                    ]
                }
            }
        )


class LiveFetchPollingTests(unittest.TestCase):
    def _pending(self):
        return {
            "2023_TX_Rollout": {
                "pat": "2023 TX Rollout",
                "proj_key": "Malaysia_CelcomDigi_Project",
                "projId": "project-1",
                "headers": {},
                "cookies": {},
            }
        }

    def test_polling_times_out_by_elapsed_time_and_reports_pending_export(self):
        clock = FakeClock()
        output = io.StringIO()

        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(output):
            result = live_fetch._poll_pending_files(
                self._pending(),
                input_dir=tmp,
                script_start_time=live_fetch.datetime.datetime(2026, 7, 14, 11, 0, 0),
                timeout_seconds=5,
                interval_seconds=4,
                requests_module=PendingRequests(),
                monotonic=clock.monotonic,
                sleeper=clock.sleep,
            )

        self.assertFalse(result)
        self.assertEqual(clock.sleeps, [4, 1])
        self.assertIn(
            "RUN_STATE stage=POLLING elapsed_seconds=0 remaining_seconds=5 "
            "pending_count=1 pending=2023_TX_Rollout",
            output.getvalue(),
        )
        self.assertIn("2023_TX_Rollout", output.getvalue())

    def test_polling_does_not_issue_record_request_after_sleep_consumes_deadline(self):
        clock = FakeClock()
        requests = TrackingPendingRequests()

        with tempfile.TemporaryDirectory() as tmp:
            result = live_fetch._poll_pending_files(
                self._pending(),
                input_dir=tmp,
                script_start_time=live_fetch.datetime.datetime(2026, 7, 14, 11, 0, 0),
                timeout_seconds=5,
                interval_seconds=5,
                requests_module=requests,
                monotonic=clock.monotonic,
                sleeper=clock.sleep,
            )

        self.assertFalse(result)
        self.assertEqual(clock.sleeps, [5])
        self.assertEqual(requests.calls, [])

    def test_polling_downloads_ready_export_before_deadline(self):
        clock = FakeClock()

        with tempfile.TemporaryDirectory() as tmp:
            result = live_fetch._poll_pending_files(
                self._pending(),
                input_dir=tmp,
                script_start_time=live_fetch.datetime.datetime(2026, 7, 14, 11, 0, 0),
                timeout_seconds=10,
                interval_seconds=2,
                requests_module=ReadyRequests(),
                monotonic=clock.monotonic,
                sleeper=clock.sleep,
            )

            export_path = os.path.join(tmp, "2023_TX_Rollout.xlsx")
            self.assertTrue(result)
            self.assertTrue(os.path.isfile(export_path))
            with open(export_path, "rb") as handle:
                self.assertEqual(handle.read(), b"fresh export")

        self.assertEqual(clock.sleeps, [2])

    def test_live_fetch_module_does_not_use_fixed_attempt_limit(self):
        with open(live_fetch.__file__, encoding="utf-8") as handle:
            source = handle.read()

        self.assertNotIn("max_polls", source)
        self.assertIn("PollWindow", source)
        self.assertIn("fetch_timeout_seconds", source)
        self.assertIn("poll_interval_seconds", source)


if __name__ == "__main__":
    unittest.main()
