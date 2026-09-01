import os
import sys
from typing import List, Optional

try:
    from . import iepms_safe_runner
except ImportError:  # Direct script execution
    import iepms_safe_runner


def _with_guarded_analyzer(argv: List[str]) -> List[str]:
    cleaned = []
    skip_next = False
    for value in argv:
        if skip_next:
            skip_next = False
            continue
        if value == "--analyzer-script":
            skip_next = True
            continue
        cleaned.append(value)

    guarded_analyzer = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "guarded_analyzer.py",
    )
    cleaned.extend(["--analyzer-script", guarded_analyzer])
    return cleaned


def run(argv: Optional[List[str]] = None) -> int:
    selected = list(sys.argv[1:] if argv is None else argv)
    require_all = "--fetch" in selected
    previous = os.environ.get("IEPMS_GUARD_REQUIRE_ALL")

    if require_all:
        os.environ["IEPMS_GUARD_REQUIRE_ALL"] = "1"
    if not require_all:
        os.environ.pop("IEPMS_GUARD_REQUIRE_ALL", None)

    try:
        return iepms_safe_runner.run(_with_guarded_analyzer(selected))
    finally:
        if previous is None:
            os.environ.pop("IEPMS_GUARD_REQUIRE_ALL", None)
        if previous is not None:
            os.environ["IEPMS_GUARD_REQUIRE_ALL"] = previous


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
