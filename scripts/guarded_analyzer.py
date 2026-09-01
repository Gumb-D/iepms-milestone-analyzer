import argparse
import os
import subprocess
import sys
from typing import List, Optional

try:
    from . import IEPMS_Milestone_Analyzer as legacy
    from .mapping_guard import (
        MappingValidationError,
        load_config,
        resolve_config_for_csvs,
        write_resolved_config,
    )
except ImportError:  # Direct script execution
    import IEPMS_Milestone_Analyzer as legacy
    from mapping_guard import (
        MappingValidationError,
        load_config,
        resolve_config_for_csvs,
        write_resolved_config,
    )


EXPECTED_CSVS = [
    "2023_TX_Rollout.csv",
    "2024_Celcomdigi_BAU.csv",
    "Jendela_TX_Migration.csv",
    "TX_Mini_Project.csv",
    "MW_EOS_Swap.csv",
    "ZTE_TX_MINI.csv",
]


def parse_args(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(
        description="Header-validated wrapper for the legacy IEPMS analyzer"
    )
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--docs-dir", required=True)
    parser.add_argument("--force-detect", action="store_true")
    parser.add_argument("--force-convert", action="store_true")
    parser.add_argument("--no-convert", action="store_true")
    return parser.parse_args(argv)


def _stream(command: List[str], cwd: str) -> int:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    if process.stdout is not None:
        for line in process.stdout:
            print(line, end="")
    return process.wait()


def _required_csvs(input_dir: str, configured) -> List[str]:
    require_all = os.environ.get("IEPMS_GUARD_REQUIRE_ALL") == "1"
    if require_all:
        return list(EXPECTED_CSVS)
    return sorted(
        filename
        for filename in configured
        if os.path.isfile(os.path.join(input_dir, filename))
    )


def run(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    legacy_script = os.path.join(script_dir, "IEPMS_Milestone_Analyzer.py")
    local_config = os.path.join(script_dir, "milestone_config.json")

    if not args.no_convert:
        legacy.check_and_convert_all_xlsx(
            os.path.abspath(args.input_dir),
            force_convert=args.force_convert,
        )

    configured = load_config(local_config, legacy.VERIFIED_MAPPINGS)
    required_csvs = _required_csvs(os.path.abspath(args.input_dir), configured)
    if not required_csvs:
        print("MAPPING_VALIDATION_FAILED: no configured CSV files were found", file=sys.stderr)
        return 2

    try:
        resolved = resolve_config_for_csvs(
            os.path.abspath(args.input_dir),
            configured,
            required_files=required_csvs,
        )
    except MappingValidationError as exc:
        print(f"MAPPING_VALIDATION_FAILED: {exc}", file=sys.stderr)
        return 2

    rebound_count = 0
    for filename in required_csvs:
        old_mapping = configured[filename]
        new_mapping = resolved[filename]
        for milestone, new_index in new_mapping.items():
            old_index = old_mapping.get(milestone)
            if old_index != new_index:
                rebound_count += 1
                print(
                    "MAPPING_REBOUND "
                    f"file={filename} milestone={milestone} "
                    f"old_index={old_index} new_index={new_index}"
                )

    verified_config = os.path.join(
        os.path.abspath(args.output_dir),
        "verified_milestone_config.json",
    )
    write_resolved_config(verified_config, resolved)
    print(
        "MAPPING_VALIDATION_COMPLETE "
        f"files={len(required_csvs)} rebound={rebound_count} "
        f"config={verified_config}"
    )

    command = [
        sys.executable,
        legacy_script,
        "--year",
        str(args.year),
        "--input-dir",
        os.path.abspath(args.input_dir),
        "--output-dir",
        os.path.abspath(args.output_dir),
        "--docs-dir",
        os.path.abspath(args.docs_dir),
        "--config",
        verified_config,
        "--no-convert",
    ]
    return _stream(command, script_dir)


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
