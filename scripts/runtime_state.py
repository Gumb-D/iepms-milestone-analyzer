import argparse
import math
import time
from typing import Callable, Iterable, Optional


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("value must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def emit_run_state(stage: str, **fields) -> str:
    parts = ["RUN_STATE", f"stage={stage}"]
    parts.extend(f"{key}={value}" for key, value in fields.items())
    line = " ".join(parts)
    print(line, flush=True)
    return line


class PollWindow:
    def __init__(
        self,
        timeout_seconds: int,
        interval_seconds: int,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if timeout_seconds <= 0 or interval_seconds <= 0:
            raise ValueError("timeout_seconds and interval_seconds must be positive")
        self.timeout_seconds = timeout_seconds
        self.interval_seconds = interval_seconds
        self._monotonic = monotonic
        self._sleeper = sleeper
        self._started = monotonic()
        self._deadline = self._started + timeout_seconds

    def elapsed(self) -> float:
        return max(0.0, self._monotonic() - self._started)

    def remaining(self) -> float:
        return max(0.0, self._deadline - self._monotonic())

    def expired(self) -> bool:
        return self.remaining() <= 0

    def snapshot(self, pending_names: Iterable[str]) -> dict:
        pending = sorted(str(name) for name in pending_names)
        return {
            "elapsed_seconds": int(math.floor(self.elapsed())),
            "remaining_seconds": int(math.ceil(self.remaining())),
            "pending_count": len(pending),
            "pending": ",".join(pending),
        }

    def sleep(self) -> float:
        duration = min(float(self.interval_seconds), self.remaining())
        if duration <= 0:
            return 0
        self._sleeper(duration)
        return duration
