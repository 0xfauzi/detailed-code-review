#!/usr/bin/env python3
"""Score code-review findings, multi-round discovery, and paired conditions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

CLASSIFICATIONS = {"bug_hit", "valid_suggestion", "noise"}
DISPOSITIONS = {"open", "accepted", "rejected", "disputed", "fixed", "deferred"}
PRIORITIES = {"P0", "P1", "P2", "P3"}
RUN_STATUSES = {"complete", "failed", "not_run"}
RESOURCE_FIELDS = ("token_count", "tool_call_count", "wall_time_seconds", "cost_usd")
METRIC_NAMES = (
    "recall",
    "macro_recall",
    "canonical_precision",
    "canonical_usefulness",
    "canonical_noise_rate",
    "delivery_precision",
    "delivery_usefulness",
    "delivery_noise_rate",
    "first_round_p1_recall",
    "macro_first_round_p1_recall",
    "p1_escape_rate",
    "late_p1_rate",
    "residual_p1_rate_at_endpoint",
    "p1_saturation_gap",
    "first_round_blocking_recognition_recall",
    "blocking_recognition_recall",
    "duplicate_burden",
    "tokens_per_unique_gold_hit",
)


class InputError(ValueError):
    """Raised when input does not match the evaluation schema."""


def read_jsonl(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    raise InputError(
                        f"{path}:{line_number}: invalid JSON: {error.msg}"
                    ) from error
                if not isinstance(row, dict):
                    raise InputError(
                        f"{path}:{line_number}: each line must contain an object"
                    )
                row["_source"] = f"{path}:{line_number}"
                row["_index"] = len(rows)
                rows.append(row)
    return rows


def require_text(row: dict[str, Any], name: str) -> str:
    value = row.get(name)
    if not isinstance(value, str) or not value:
        raise InputError(f"{row['_source']}: {name} must be a non-empty string")
    return value


def optional_number(row: dict[str, Any], name: str) -> int | float | None:
    value = row.get(name)
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise InputError(f"{row['_source']}: {name} must be a non-negative number")
    return value


def ratio(numerator: float, denominator: float) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 6)


def difference(left: float | None, right: float | None) -> float | None:
    return None if left is None or right is None else round(left - right, 6)


def load_cases(paths: list[Path]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(paths):
        if row.get("schema_version") != 1:
            raise InputError(f"{row['_source']}: schema_version must be 1")
        case_id = require_text(row, "case_id")
        if case_id in cases:
            raise InputError(f"{row['_source']}: duplicate case_id {case_id}")
        diff = require_text(row, "diff")
        computed_hash = hashlib.sha256(diff.encode()).hexdigest()
        supplied_hash = row.get("diff_sha256", computed_hash)
        try:
            valid_hash = len(supplied_hash) == 64 and int(supplied_hash, 16) >= 0
        except (TypeError, ValueError):
            valid_hash = False
        if not valid_hash or supplied_hash != computed_hash:
            raise InputError(f"{row['_source']}: diff_sha256 does not match diff")
        findings = row.get("gold_findings")
        if not isinstance(findings, list):
            raise InputError(f"{row['_source']}: gold_findings must be a list")
        gold: dict[str, dict[str, Any]] = {}
        for finding in findings:
            if not isinstance(finding, dict) or not isinstance(finding.get("id"), str):
                raise InputError(
                    f"{row['_source']}: each gold finding needs a string id"
                )
            gold_id = finding["id"]
            if not gold_id or gold_id in gold:
                raise InputError(
                    f"{row['_source']}: invalid or duplicate gold id {gold_id!r}"
                )
            if finding.get("priority") not in PRIORITIES:
                raise InputError(
                    f"{row['_source']}: gold finding {gold_id} has invalid priority"
                )
            if finding.get("present_in_initial_target", True) is not True:
                raise InputError(
                    f"{row['_source']}: a changed target requires a new case"
                )
            gold[gold_id] = finding
        cases[case_id] = {
            "benchmark": require_text(row, "benchmark"),
            "repository": require_text(row, "repository"),
            "base_revision": require_text(row, "base_revision"),
            "target_revision": require_text(row, "target_revision"),
            "diff_sha256": computed_hash,
            "gold": gold,
        }
    if not cases:
        raise InputError("No cases were loaded")
    return cases


def validate_run_sequences(runs: dict[str, dict[str, Any]]) -> None:
    grouped: dict[tuple[str, str, str], dict[int, dict[str, Any]]] = defaultdict(dict)
    for run in runs.values():
        key = (run["case_id"], run["condition"], run["replicate_id"])
        if run["round"] in grouped[key]:
            raise InputError(
                f"{run['_source']}: duplicate round {run['round']} for {key}"
            )
        grouped[key][run["round"]] = run
    for key, by_round in grouped.items():
        for number, run in by_round.items():
            if run["status"] != "complete":
                continue
            for earlier in range(1, number):
                if by_round.get(earlier, {}).get("status") != "complete":
                    raise InputError(
                        f"{run['_source']}: completed round {number} for {key} "
                        f"requires completed round {earlier}"
                    )


def load_runs(
    path: Path, cases: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    runs: dict[str, dict[str, Any]] = {}
    for row in read_jsonl([path]):
        if row.get("schema_version") != 1:
            raise InputError(f"{row['_source']}: schema_version must be 1")
        run_id = require_text(row, "run_id")
        case_id = require_text(row, "case_id")
        if run_id in runs:
            raise InputError(f"{row['_source']}: duplicate run_id {run_id}")
        if case_id not in cases:
            raise InputError(f"{row['_source']}: unknown case_id {case_id}")
        number = row.get("round")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise InputError(f"{row['_source']}: round must be a positive integer")
        if row.get("status") not in RUN_STATUSES:
            raise InputError(
                f"{row['_source']}: invalid run status {row.get('status')!r}"
            )
        case = cases[case_id]
        for field in ("repository", "base_revision", "target_revision", "diff_sha256"):
            if require_text(row, field) != case[field]:
                raise InputError(
                    f"{row['_source']}: {field} does not match case {case_id}"
                )
        runs[run_id] = {
            **row,
            "condition": require_text(row, "condition"),
            "replicate_id": require_text(row, "replicate_id"),
            "resources": {
                field: optional_number(row, field) for field in RESOURCE_FIELDS
            },
        }
    if not runs:
        raise InputError("No runs were loaded")
    validate_run_sequences(runs)
    return runs


def parse_finding(row: dict[str, Any], cases: dict[str, dict[str, Any]]) -> None:
    case_id = require_text(row, "case_id")
    require_text(row, "finding_id")
    require_text(row, "reason")
    if case_id not in cases:
        raise InputError(f"{row['_source']}: unknown case_id {case_id}")
    if row.get("classification") not in CLASSIFICATIONS:
        raise InputError(f"{row['_source']}: invalid classification")
    if row.get("disposition") not in DISPOSITIONS:
        raise InputError(f"{row['_source']}: invalid disposition")
    priority = row.get("predicted_priority")
    if priority is not None and priority not in PRIORITIES:
        raise InputError(f"{row['_source']}: invalid predicted_priority {priority!r}")
    duplicate = row.get("duplicate_of")
    if duplicate is not None and (not isinstance(duplicate, str) or not duplicate):
        raise InputError(f"{row['_source']}: invalid duplicate_of")
    root = row.get("root_cause_id")
    if root is not None and (not isinstance(root, str) or not root):
        raise InputError(f"{row['_source']}: invalid root_cause_id")
    gold_ids = row.get("gold_bug_ids")
    if not isinstance(gold_ids, list) or any(
        not isinstance(item, str) for item in gold_ids
    ):
        raise InputError(f"{row['_source']}: gold_bug_ids must be a list of strings")
    if len(gold_ids) != len(set(gold_ids)):
        raise InputError(f"{row['_source']}: gold_bug_ids contains duplicates")
    unknown = set(gold_ids) - set(cases[case_id]["gold"])
    if unknown:
        raise InputError(f"{row['_source']}: unknown gold ids {sorted(unknown)}")
    if row["classification"] == "bug_hit" and not gold_ids:
        raise InputError(f"{row['_source']}: bug_hit requires a gold id")
    if row["classification"] != "bug_hit" and gold_ids:
        raise InputError(f"{row['_source']}: only bug_hit can reference gold ids")
    row.update(predicted_priority=priority, duplicate_of=duplicate, root_cause_id=root)


def infer_legacy_runs(
    findings: list[dict[str, Any]], cases: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    condition_replicates = {
        (row["condition"], row["replicate_id"]) for row in findings
    } or {("default", "legacy-1")}
    endpoints: dict[tuple[str, str, str], int] = defaultdict(lambda: 1)
    for row in findings:
        key = (row["case_id"], row["condition"], row["replicate_id"])
        endpoints[key] = max(endpoints[key], row["round"])
    runs: dict[str, dict[str, Any]] = {}
    for case_id, case in cases.items():
        for condition, replicate in condition_replicates:
            for number in range(1, endpoints[(case_id, condition, replicate)] + 1):
                run_id = f"legacy::{case_id}::{condition}::{replicate}::{number}"
                runs[run_id] = {
                    "_source": "inferred legacy run",
                    "run_id": run_id,
                    "case_id": case_id,
                    "condition": condition,
                    "replicate_id": replicate,
                    "round": number,
                    "status": "complete",
                    "repository": case["repository"],
                    "base_revision": case["base_revision"],
                    "target_revision": case["target_revision"],
                    "diff_sha256": case["diff_sha256"],
                    "resources": {field: None for field in RESOURCE_FIELDS},
                }
    return runs


def load_findings(
    path: Path,
    cases: dict[str, dict[str, Any]],
    explicit_runs: dict[str, dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    findings = read_jsonl([path])
    for row in findings:
        parse_finding(row, cases)
    if explicit_runs is None:
        for row in findings:
            condition = row.get("condition", "default")
            replicate = row.get("replicate_id", "legacy-1")
            number = row.get("round", 1)
            if not isinstance(condition, str) or not condition:
                raise InputError(f"{row['_source']}: invalid condition")
            if not isinstance(replicate, str) or not replicate:
                raise InputError(f"{row['_source']}: invalid replicate_id")
            if not isinstance(number, int) or isinstance(number, bool) or number < 1:
                raise InputError(f"{row['_source']}: invalid round")
            row.update(condition=condition, replicate_id=replicate, round=number)
        runs = infer_legacy_runs(findings, cases)
        for row in findings:
            row["run_id"] = (
                f"legacy::{row['case_id']}::{row['condition']}::"
                f"{row['replicate_id']}::{row['round']}"
            )
    else:
        runs = explicit_runs
        for row in findings:
            run_id = require_text(row, "run_id")
            if run_id not in runs:
                raise InputError(f"{row['_source']}: unknown run_id {run_id}")
            run = runs[run_id]
            if run["status"] != "complete":
                raise InputError(f"{row['_source']}: findings require a completed run")
            if row["case_id"] != run["case_id"]:
                raise InputError(
                    f"{row['_source']}: case_id does not match run {run_id}"
                )
            for field in ("condition", "replicate_id", "round"):
                if field in row and row[field] != run[field]:
                    raise InputError(
                        f"{row['_source']}: {field} does not match run {run_id}"
                    )
            row.update(
                condition=run["condition"],
                replicate_id=run["replicate_id"],
                round=run["round"],
            )

    index: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in findings:
        key = (row["case_id"], row["condition"], row["replicate_id"], row["finding_id"])
        if key in index:
            raise InputError(f"{row['_source']}: duplicate finding id in {key[:3]}")
        index[key] = row
    for row in findings:
        duplicate = row["duplicate_of"]
        if duplicate is None:
            continue
        key = (row["case_id"], row["condition"], row["replicate_id"], duplicate)
        target = index.get(key)
        if target is None or target["duplicate_of"] is not None:
            raise InputError(
                f"{row['_source']}: duplicate_of must reference a canonical finding"
            )
        target_is_later = target["round"] > row["round"] or (
            target["round"] == row["round"] and target["_index"] >= row["_index"]
        )
        if duplicate == row["finding_id"] or target_is_later:
            raise InputError(
                f"{row['_source']}: duplicate_of must reference an earlier finding"
            )
        if target["classification"] != row["classification"]:
            raise InputError(f"{row['_source']}: duplicate classifications differ")
        if row["classification"] == "bug_hit":
            if set(target["gold_bug_ids"]) != set(row["gold_bug_ids"]):
                raise InputError(f"{row['_source']}: duplicate gold ids differ")
        elif (
            not row["root_cause_id"] or row["root_cause_id"] != target["root_cause_id"]
        ):
            raise InputError(
                f"{row['_source']}: non-bug duplicates need one root cause"
            )

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in findings:
        grouped[(row["case_id"], row["condition"], row["replicate_id"])].append(row)
    for key, rows in grouped.items():
        seen_gold: set[str] = set()
        seen_roots: set[str] = set()
        for row in sorted(rows, key=lambda item: (item["round"], item["_index"])):
            if row["duplicate_of"] is not None:
                continue
            root = row["root_cause_id"]
            if root and root in seen_roots:
                raise InputError(
                    f"{row['_source']}: repeated root cause in {key} needs duplicate_of"
                )
            if root:
                seen_roots.add(root)
            if row["classification"] == "bug_hit":
                current = set(row["gold_bug_ids"])
                if current <= seen_gold:
                    raise InputError(
                        f"{row['_source']}: repeated gold hit in {key} needs duplicate_of"
                    )
                seen_gold.update(current)
    return findings, runs


def completed_units(runs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[int, dict[str, Any]]] = defaultdict(dict)
    for run in runs.values():
        grouped[(run["case_id"], run["condition"], run["replicate_id"])][
            run["round"]
        ] = run
    units: list[dict[str, Any]] = []
    for (case_id, condition, replicate), by_round in sorted(grouped.items()):
        endpoint = 0
        while by_round.get(endpoint + 1, {}).get("status") == "complete":
            endpoint += 1
        if endpoint:
            units.append(
                {
                    "case_id": case_id,
                    "condition": condition,
                    "replicate_id": replicate,
                    "endpoint": endpoint,
                    "runs": {
                        number: by_round[number] for number in range(1, endpoint + 1)
                    },
                }
            )
    return units


def resource_summary(units: list[dict[str, Any]]) -> dict[str, Any]:
    runs = [run for unit in units for run in unit["runs"].values()]
    result: dict[str, Any] = {"completed_run_count": len(runs)}
    for field in RESOURCE_FIELDS:
        values = [
            run["resources"][field]
            for run in runs
            if run["resources"][field] is not None
        ]
        result[field] = {
            "total": round(sum(values), 6)
            if values and len(values) == len(runs)
            else None,
            "observed_run_count": len(values),
        }
    return result


def score_units(
    units: list[dict[str, Any]],
    cases: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
    condition: str,
) -> dict[str, Any]:
    run_ids = {run["run_id"] for unit in units for run in unit["runs"].values()}
    raw = [row for row in findings if row["run_id"] in run_ids]
    canonical = [row for row in raw if row["duplicate_of"] is None]
    unit_keys = {(unit["case_id"], unit["replicate_id"]) for unit in units}
    gold = {
        (case_id, replicate, gold_id)
        for case_id, replicate in unit_keys
        for gold_id in cases[case_id]["gold"]
    }
    hit_round: dict[tuple[str, str, str], int] = {}
    for row in canonical:
        if row["classification"] == "bug_hit":
            for gold_id in row["gold_bug_ids"]:
                key = (row["case_id"], row["replicate_id"], gold_id)
                hit_round[key] = min(hit_round.get(key, row["round"]), row["round"])
    hit = set(hit_round)
    p1_gold = {key for key in gold if cases[key[0]]["gold"][key[2]]["priority"] == "P1"}
    hit_p1 = hit & p1_gold
    first_p1 = {key for key in hit_p1 if hit_round[key] == 1}
    late_p1 = {key for key in hit_p1 if hit_round[key] > 1}
    residual_p1 = p1_gold - hit_p1

    p1_rows = [
        row
        for row in canonical
        if row["classification"] == "bug_hit"
        and any(
            (row["case_id"], row["replicate_id"], item) in p1_gold
            for item in row["gold_bug_ids"]
        )
    ]
    first_p1_rows = [row for row in p1_rows if row["round"] == 1]
    priority_coverage = ratio(
        sum(row["predicted_priority"] is not None for row in p1_rows), len(p1_rows)
    )
    first_priority_coverage = ratio(
        sum(row["predicted_priority"] is not None for row in first_p1_rows),
        len(first_p1_rows),
    )

    def recognized(rows: list[dict[str, Any]]) -> set[tuple[str, str, str]]:
        return {
            (row["case_id"], row["replicate_id"], item)
            for row in rows
            if row["predicted_priority"] in {"P0", "P1"}
            for item in row["gold_bug_ids"]
            if (row["case_id"], row["replicate_id"], item) in p1_gold
        }

    def recognition(rows: list[dict[str, Any]], coverage: float | None) -> float | None:
        if not rows:
            return ratio(0, len(p1_gold))
        return ratio(len(recognized(rows)), len(p1_gold)) if coverage == 1.0 else None

    counts = Counter(row["classification"] for row in canonical)
    raw_count = len(raw)
    canonical_count = len(canonical)
    duplicate_count = raw_count - canonical_count
    useful = counts["bug_hit"] + counts["valid_suggestion"]
    noise = counts["noise"]
    burden = noise + duplicate_count
    first_recall = ratio(len(first_p1), len(p1_gold))
    final_recall = ratio(len(hit_p1), len(p1_gold))
    unit_recalls: list[float] = []
    unit_p1_recalls: list[float] = []
    for case_id, replicate in sorted(unit_keys):
        unit_gold = {key for key in gold if key[:2] == (case_id, replicate)}
        unit_p1 = unit_gold & p1_gold
        unit_recall = ratio(len(unit_gold & hit), len(unit_gold))
        unit_p1_recall = ratio(len(unit_p1 & first_p1), len(unit_p1))
        if unit_recall is not None:
            unit_recalls.append(unit_recall)
        if unit_p1_recall is not None:
            unit_p1_recalls.append(unit_p1_recall)

    rounds: dict[str, dict[str, Any]] = {}
    for number in range(1, max((unit["endpoint"] for unit in units), default=0) + 1):
        eligible = [unit for unit in units if unit["endpoint"] >= number]
        eligible_keys = {(unit["case_id"], unit["replicate_id"]) for unit in eligible}
        eligible_gold = {key for key in gold if (key[0], key[1]) in eligible_keys}
        eligible_p1 = eligible_gold & p1_gold
        raw_round = [
            row
            for row in raw
            if row["round"] == number
            and (row["case_id"], row["replicate_id"]) in eligible_keys
        ]
        canonical_round = [row for row in raw_round if row["duplicate_of"] is None]
        round_counts = Counter(row["classification"] for row in canonical_round)
        new_gold = {
            key
            for key, first in hit_round.items()
            if first == number and key in eligible_gold
        }
        cumulative = {
            key
            for key, first in hit_round.items()
            if first <= number and key in eligible_gold
        }
        new_comments = sum(
            row["classification"] == "bug_hit"
            and any(
                (row["case_id"], row["replicate_id"], item) in new_gold
                for item in row["gold_bug_ids"]
            )
            for row in canonical_round
        )
        duplicates = len(raw_round) - len(canonical_round)
        round_burden = round_counts["noise"] + duplicates
        rounds[str(number)] = {
            "eligible_review_unit_count": len(eligible),
            "raw_finding_count": len(raw_round),
            "canonical_finding_count": len(canonical_round),
            "new_gold_bug_count": len(new_gold),
            "new_p1_count": len(new_gold & eligible_p1),
            "cumulative_gold_bug_count": len(cumulative),
            "cumulative_recall": ratio(len(cumulative), len(eligible_gold)),
            "cumulative_p1_hit_count": len(cumulative & eligible_p1),
            "cumulative_p1_recall": ratio(
                len(cumulative & eligible_p1), len(eligible_p1)
            ),
            "noise_count": round_counts["noise"],
            "duplicate_count": duplicates,
            "comment_noise_rate": ratio(round_burden, len(raw_round)),
            "duplicate_burden": ratio(duplicates, len(raw_round)),
            "marginal_signal_to_noise": ratio(
                new_comments + round_counts["valid_suggestion"], round_burden
            ),
        }

    canonical_precision = ratio(counts["bug_hit"], canonical_count)
    canonical_usefulness = ratio(useful, canonical_count)
    canonical_noise_rate = ratio(noise, canonical_count)
    endpoint_counts = Counter(unit["endpoint"] for unit in units)
    resources = resource_summary(units)
    token_total = resources["token_count"]["total"]
    result = {
        "condition": condition,
        "case_count": len({unit["case_id"] for unit in units}),
        "review_unit_count": len(units),
        "endpoint_rounds": {
            str(key): endpoint_counts[key] for key in sorted(endpoint_counts)
        },
        "gold_bug_count": len(gold),
        "hit_gold_bug_count": len(hit),
        "raw_finding_count": raw_count,
        "canonical_finding_count": canonical_count,
        "finding_count": canonical_count,
        "duplicate_count": duplicate_count,
        "bug_hit_count": counts["bug_hit"],
        "valid_suggestion_count": counts["valid_suggestion"],
        "useful_finding_count": useful,
        "false_positive_count": noise,
        "recall": ratio(len(hit), len(gold)),
        "macro_recall": ratio(sum(unit_recalls), len(unit_recalls)),
        "canonical_precision": canonical_precision,
        "canonical_usefulness": canonical_usefulness,
        "canonical_noise_rate": canonical_noise_rate,
        "canonical_signal_to_noise": ratio(useful, noise),
        "delivery_precision": ratio(counts["bug_hit"], raw_count),
        "delivery_usefulness": ratio(useful, raw_count),
        "delivery_noise_rate": ratio(burden, raw_count),
        "delivery_signal_to_noise": ratio(useful, burden),
        # Legacy aliases remain canonical and preserve old smoke reports.
        "precision": canonical_precision,
        "usefulness": canonical_usefulness,
        "false_positive_rate": canonical_noise_rate,
        "signal_to_noise": ratio(useful, noise),
        "duplicate_burden": ratio(duplicate_count, raw_count),
        "p1_gold_count": len(p1_gold),
        "p1_hit_count": len(hit_p1),
        "first_round_p1_hit_count": len(first_p1),
        "late_p1_count": len(late_p1),
        "residual_p1_count_at_endpoint": len(residual_p1),
        "first_round_p1_recall": first_recall,
        "macro_first_round_p1_recall": ratio(
            sum(unit_p1_recalls), len(unit_p1_recalls)
        ),
        "final_p1_recall": final_recall,
        "p1_escape_rate": ratio(len(p1_gold) - len(first_p1), len(p1_gold)),
        "late_p1_rate": ratio(len(late_p1), len(p1_gold)),
        "conditional_late_p1_share": ratio(len(late_p1), len(hit_p1)),
        "residual_p1_rate_at_endpoint": ratio(len(residual_p1), len(p1_gold)),
        "residual_p1_rate": ratio(len(residual_p1), len(p1_gold)),
        "p1_saturation_gap": difference(final_recall, first_recall),
        "priority_label_coverage": priority_coverage,
        "first_round_priority_label_coverage": first_priority_coverage,
        "first_round_blocking_recognition_recall": recognition(
            first_p1_rows, first_priority_coverage
        ),
        "blocking_recognition_recall": recognition(p1_rows, priority_coverage),
        "resources": resources,
        "tokens_per_unique_gold_hit": (
            ratio(token_total, len(hit)) if token_total is not None else None
        ),
        "dispositions": dict(
            sorted(Counter(row["disposition"] for row in raw).items())
        ),
        "rounds": rounds,
    }
    return result


def metric_deltas(
    current: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, float | None]:
    return {
        name: difference(current.get(name), baseline.get(name))
        if isinstance(current.get(name), (int, float))
        and isinstance(baseline.get(name), (int, float))
        else None
        for name in METRIC_NAMES
    }


def compare_conditions(
    control: str,
    treatment: str,
    units: list[dict[str, Any]],
    cases: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    if control == treatment:
        raise InputError("Control and treatment conditions must differ")
    control_units = {
        (unit["case_id"], unit["replicate_id"]): unit
        for unit in units
        if unit["condition"] == control
    }
    treatment_units = {
        (unit["case_id"], unit["replicate_id"]): unit
        for unit in units
        if unit["condition"] == treatment
    }
    paired = sorted(set(control_units) & set(treatment_units))
    if not paired:
        raise InputError("The conditions have no completed paired review units")
    control_score = score_units(
        [control_units[key] for key in paired], cases, findings, control
    )
    treatment_score = score_units(
        [treatment_units[key] for key in paired], cases, findings, treatment
    )
    endpoints_match = all(
        control_units[key]["endpoint"] == treatment_units[key]["endpoint"]
        for key in paired
    )
    deltas = metric_deltas(treatment_score, control_score)
    if not endpoints_match:
        for name in (
            "late_p1_rate",
            "residual_p1_rate_at_endpoint",
            "p1_saturation_gap",
        ):
            deltas[name] = None
    per_pair: list[dict[str, Any]] = []
    macro_values: list[float] = []
    for key in paired:
        left = score_units([control_units[key]], cases, findings, control)
        right = score_units([treatment_units[key]], cases, findings, treatment)
        uplift = difference(
            right["first_round_p1_recall"], left["first_round_p1_recall"]
        )
        if uplift is not None:
            macro_values.append(uplift)
        per_pair.append(
            {
                "case_id": key[0],
                "replicate_id": key[1],
                "control_endpoint": control_units[key]["endpoint"],
                "treatment_endpoint": treatment_units[key]["endpoint"],
                "first_round_p1_recall_uplift": uplift,
            }
        )
    resource_ratios = {
        field: ratio(
            treatment_score["resources"][field]["total"],
            control_score["resources"][field]["total"],
        )
        if treatment_score["resources"][field]["total"] is not None
        and control_score["resources"][field]["total"] is not None
        else None
        for field in RESOURCE_FIELDS
    }
    return {
        "control": control,
        "treatment": treatment,
        "paired_review_unit_count": len(paired),
        "paired_case_count": len({key[0] for key in paired}),
        "control_only_review_unit_count": len(
            set(control_units) - set(treatment_units)
        ),
        "treatment_only_review_unit_count": len(
            set(treatment_units) - set(control_units)
        ),
        "endpoint_matched_pair_count": sum(
            control_units[key]["endpoint"] == treatment_units[key]["endpoint"]
            for key in paired
        ),
        "metric_deltas": deltas,
        "p1_recall_uplift": difference(
            treatment_score["first_round_p1_recall"],
            control_score["first_round_p1_recall"],
        ),
        "macro_p1_recall_uplift": ratio(sum(macro_values), len(macro_values)),
        "late_p1_reduction": difference(
            control_score["late_p1_rate"], treatment_score["late_p1_rate"]
        )
        if endpoints_match
        else None,
        "noise_delta": difference(
            treatment_score["canonical_noise_rate"],
            control_score["canonical_noise_rate"],
        ),
        "delivery_noise_delta": difference(
            treatment_score["delivery_noise_rate"], control_score["delivery_noise_rate"]
        ),
        "duplicate_burden_delta": difference(
            treatment_score["duplicate_burden"], control_score["duplicate_burden"]
        ),
        "resource_ratios": resource_ratios,
        "cost_ratio": resource_ratios["cost_usd"],
        "token_ratio": resource_ratios["token_count"],
        "per_pair": per_pair,
    }


def build_report(
    cases: dict[str, dict[str, Any]],
    runs: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
    baseline: dict[str, Any] | None,
    control: str | None,
    treatment: str | None,
    run_mode: str,
) -> dict[str, Any]:
    units = completed_units(runs)
    conditions = sorted({run["condition"] for run in runs.values()})
    by_condition = {
        condition: score_units(
            [unit for unit in units if unit["condition"] == condition],
            cases,
            findings,
            condition,
        )
        for condition in conditions
    }
    benchmark_units: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in units:
        benchmark_units[cases[unit["case_id"]]["benchmark"]].append(unit)
    statuses = Counter(run["status"] for run in runs.values())
    report: dict[str, Any] = {
        "schema_version": 3,
        "run_mode": run_mode,
        "run_statuses": {name: statuses[name] for name in sorted(RUN_STATUSES)},
        "case_provenance": {
            case_id: {
                field: case[field]
                for field in (
                    "repository",
                    "base_revision",
                    "target_revision",
                    "diff_sha256",
                )
            }
            for case_id, case in sorted(cases.items())
        },
        "by_condition": by_condition,
        "by_benchmark": {
            benchmark: {
                condition: score_units(
                    [
                        unit
                        for unit in benchmark_units[benchmark]
                        if unit["condition"] == condition
                    ],
                    cases,
                    findings,
                    condition,
                )
                for condition in conditions
            }
            for benchmark in sorted(benchmark_units)
        },
    }
    if len(conditions) == 1:
        report["aggregate"] = by_condition[conditions[0]]
    if baseline is not None:
        if len(conditions) != 1:
            raise InputError("A baseline requires one condition")
        previous = baseline.get("aggregate", baseline)
        if not isinstance(previous, dict):
            raise InputError("The baseline report must contain an aggregate object")
        report["delta_from_baseline"] = metric_deltas(
            by_condition[conditions[0]], previous
        )
    if (control is None) != (treatment is None):
        raise InputError("Set both control and treatment conditions")
    if control is not None and treatment is not None:
        missing = {control, treatment} - set(conditions)
        if missing:
            raise InputError(f"Unknown comparison conditions: {sorted(missing)}")
        report["condition_comparison"] = compare_conditions(
            control, treatment, units, cases, findings
        )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="+", type=Path, required=True)
    parser.add_argument("--runs", type=Path)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--baseline-report", type=Path)
    parser.add_argument("--control-condition")
    parser.add_argument("--treatment-condition")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        cases = load_cases(args.cases)
        explicit_runs = load_runs(args.runs, cases) if args.runs else None
        findings, runs = load_findings(args.judgments, cases, explicit_runs)
        baseline = None
        if args.baseline_report:
            baseline = json.loads(args.baseline_report.read_text(encoding="utf-8"))
        report = build_report(
            cases,
            runs,
            findings,
            baseline,
            args.control_condition,
            args.treatment_condition,
            "explicit" if args.runs else "legacy_inferred",
        )
    except (InputError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
