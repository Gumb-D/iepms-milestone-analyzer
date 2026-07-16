import csv
import json
import os
from typing import Dict, Iterable, List, Mapping, Optional, Sequence


MILESTONE_KEYWORDS = {
    "SOW": {
        "primary": ("tx planning", "sow", "scope of work"),
        "stage": ("tx planning", "commercial", "planner"),
    },
    "TSS": {
        "primary": (
            "physical survey",
            "tssr customer approval",
            "tssr submitted to customer",
            "e-tss",
        ),
        "stage": ("survey", "design", "rollout", "etss"),
    },
    "MC": {
        "primary": ("material collection", "material collect"),
        "stage": ("ready for installation", "warehouse", "installation"),
    },
    "MOS": {
        "primary": ("material on site", "material on-site"),
        "stage": ("material on site", "rollout", "warehouse"),
    },
    "TI": {
        "primary": ("equipment installation", "telecom installation", "equipment install"),
        "stage": ("telecom installation", "rollout", "installation"),
    },
    "L1": {
        "primary": ("l1 approved", "l1 report", "line 1"),
        "stage": ("q&ehs", "pac site binder complete"),
    },
    "RFS": {
        "primary": (
            "site integrated",
            "tx integrated",
            "tx integration end date",
            "cut-over end date",
            "cutover end date",
            "cut over",
            "cutover",
        ),
        "stage": ("software commissioning", "operation", "installation"),
    },
    "PAC": {
        "primary": (
            "pac approved",
            "preliminary acceptance certification",
            "provisional acceptance",
        ),
        "stage": ("preliminary/provisional", "acceptance certification", "pac work complete"),
    },
}

# File-specific business identities take precedence over generic milestone keywords.
# They prevent another task with a valid-looking actual-end field from being used as
# the milestone merely because its wording scores similarly.
REQUIRED_IDENTITIES = {
    ("2023_TX_Rollout.csv", "TSS"): {
        "stage": "survey&design",
        "task": "physical survey",
    },
    ("2023_TX_Rollout.csv", "L1"): {
        "stage": "q&ehs",
        "task": "l1 approved",
    },
    ("2024_Celcomdigi_BAU.csv", "TSS"): {
        "stage": "survey&design",
        "task": "tssr customer approval",
    },
    ("Jendela_TX_Migration.csv", "RFS"): {
        "stage": "software commissioning",
        "task": "cut over",
    },
    ("TX_Mini_Project.csv", "RFS"): {
        "stage": "software commissioning",
        "task": "tx integrated",
    },
}

# Some DU models do not implement every standard milestone. These explicit N/A
# declarations override stale integer hints and prevent unrelated fields from being
# substituted merely to keep the report running.
UNAVAILABLE_MILESTONES = {
    ("Jendela_TX_Migration.csv", "TSS"),
}


class MappingValidationError(ValueError):
    pass


def _normalise(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _column_values(headers: Sequence[Sequence[str]], index: int) -> List[str]:
    return [
        str(row[index]).strip() if index < len(row) else ""
        for row in headers[:4]
    ]


def _matches_required_identity(
    filename: str,
    milestone: str,
    values: Sequence[str],
) -> bool:
    required = REQUIRED_IDENTITIES.get((filename, milestone))
    if required is None:
        return True

    _field_id, stage, task, _display = (_normalise(value) for value in values)
    return stage == required["stage"] and task == required["task"]


def _is_actual_completion(milestone: str, values: Sequence[str]) -> bool:
    field_id, _stage, _task, display = (_normalise(value) for value in values)
    identity = f"{field_id} {display}"

    planned_tokens = (
        "planned",
        "plan end",
        "plan_end",
        "planned_end",
        "planned start",
        "plan start",
    )
    if any(token in identity for token in planned_tokens):
        return False

    start_tokens = ("actual_start_date", "actual start time", "actual start date")
    if any(token in identity for token in start_tokens):
        return False

    if "actual_end_date" in field_id:
        return True
    if "actual end time" in display or "actual end date" in display:
        return True

    if milestone == "RFS":
        special_rfs_headers = (
            "tx integration end date",
            "integration end date",
            "cut-over end date",
            "cutover end date",
        )
        if any(token in display for token in special_rfs_headers):
            return True

    return False


def _candidate_score(milestone: str, values: Sequence[str]) -> int:
    keyword_info = MILESTONE_KEYWORDS.get(milestone)
    if not keyword_info:
        return 0

    combined = " | ".join(_normalise(value) for value in values)
    score = sum(10 for token in keyword_info["primary"] if token in combined)
    score += sum(2 for token in keyword_info["stage"] if token in combined)
    return score


def resolve_mapping_indices(
    filename: str,
    headers: Sequence[Sequence[str]],
    configured_mapping: Mapping[str, Optional[int]],
) -> Dict[str, Optional[int]]:
    if len(headers) < 4:
        raise MappingValidationError(
            f"{filename}: expected four header rows, found {len(headers)}"
        )

    column_count = max((len(row) for row in headers[:4]), default=0)
    if column_count == 0:
        raise MappingValidationError(f"{filename}: header rows are empty")

    resolved: Dict[str, Optional[int]] = {}

    for milestone, hint in configured_mapping.items():
        if (filename, milestone) in UNAVAILABLE_MILESTONES:
            resolved[milestone] = None
            continue

        if hint is None:
            resolved[milestone] = None
            continue

        scored_candidates = []
        for index in range(column_count):
            values = _column_values(headers, index)
            if not _matches_required_identity(filename, milestone, values):
                continue
            if not _is_actual_completion(milestone, values):
                continue
            score = _candidate_score(milestone, values)
            if score >= 10:
                scored_candidates.append((score, index, values))

        if not scored_candidates:
            required = REQUIRED_IDENTITIES.get((filename, milestone))
            identity_note = ""
            if required is not None:
                identity_note = (
                    f"; required stage/task is "
                    f"{required['stage']} / {required['task']}"
                )
            raise MappingValidationError(
                f"{filename} {milestone}: no unique actual-completion header matches; "
                f"configured index {hint} is not trusted{identity_note}"
            )

        best_score = max(score for score, _index, _values in scored_candidates)
        best = [item for item in scored_candidates if item[0] == best_score]

        if len(best) != 1:
            indexes = ",".join(str(index) for _score, index, _values in best)
            raise MappingValidationError(
                f"{filename} {milestone}: ambiguous actual-completion headers at indexes {indexes}"
            )

        _score, resolved_index, _values = best[0]
        resolved[milestone] = resolved_index

    return resolved


def read_csv_headers(path: str) -> List[List[str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        headers = []
        for _ in range(4):
            row = next(reader, None)
            if row is None:
                break
            headers.append(row)
    return headers


def resolve_config_for_csvs(
    input_dir: str,
    configured: Mapping[str, Mapping[str, Optional[int]]],
    *,
    required_files: Optional[Iterable[str]] = None,
) -> Dict[str, Dict[str, Optional[int]]]:
    required = set(required_files or configured.keys())
    resolved = {}

    for filename in sorted(required):
        mapping = configured.get(filename)
        if mapping is None:
            raise MappingValidationError(f"{filename}: no configured milestone mapping")

        csv_path = os.path.join(input_dir, filename)
        if not os.path.isfile(csv_path):
            raise MappingValidationError(f"{filename}: CSV file is missing")

        headers = read_csv_headers(csv_path)
        resolved[filename] = resolve_mapping_indices(filename, headers, mapping)

    return resolved


def load_config(path: str, fallback: Mapping[str, Mapping[str, Optional[int]]]):
    if not os.path.isfile(path):
        return {name: dict(mapping) for name, mapping in fallback.items()}
    with open(path, "r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    return loaded


def write_resolved_config(path: str, mappings: Mapping[str, Mapping[str, Optional[int]]]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(mappings, handle, indent=4)
