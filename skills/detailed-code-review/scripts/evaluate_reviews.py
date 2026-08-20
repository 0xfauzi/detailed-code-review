#!/usr/bin/env python3
"""Score normalized code-review judgments."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CLASSIFICATIONS = {"bug_hit", "valid_suggestion", "noise"}
DISPOSITIONS = {"open", "accepted", "rejected", "disputed", "fixed", "deferred"}
METRIC_NAMES = ("recall", "precision", "usefulness", "false_positive_rate", "signal_to_noise")


class InputError(ValueError):
    """Raised when an evaluation input does not match the schema."""


def read_jsonl(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    raise InputError(f"{path}:{line_number}: invalid JSON: {error.msg}") from error
                if not isinstance(row, dict):
                    raise InputError(f"{path}:{line_number}: each line must contain an object")
                row["_source"] = f"{path}:{line_number}"
                rows.append(row)
    return rows


def require_text(row: dict[str, Any], name: str) -> str:
    value = row.get(name)
    if not isinstance(value, str) or not value:
        raise InputError(f"{row['_source']}: {name} must be a non-empty string")
    return value


def load_cases(paths: list[Path]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(paths):
        case_id = require_text(row, "case_id")
        benchmark = require_text(row, "benchmark")
        if case_id in cases:
            raise InputError(f"{row['_source']}: duplicate case_id {case_id}")
        findings = row.get("gold_findings")
        if not isinstance(findings, list):
            raise InputError(f"{row['_source']}: gold_findings must be a list")
        gold_ids: set[str] = set()
        for finding in findings:
            if not isinstance(finding, dict) or not isinstance(finding.get("id"), str):
                raise InputError(f"{row['_source']}: each gold finding needs a string id")
            gold_id = finding["id"]
            if gold_id in gold_ids:
                raise InputError(f"{row['_source']}: duplicate gold finding id {gold_id}")
            gold_ids.add(gold_id)
        cases[case_id] = {"benchmark": benchmark, "gold_ids": gold_ids}
    if not cases:
        raise InputError("No cases were loaded")
    return cases


def load_judgments(path: Path, cases: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    judgments = read_jsonl([path])
    seen: set[tuple[str, str]] = set()
    for row in judgments:
        case_id = require_text(row, "case_id")
        finding_id = require_text(row, "finding_id")
        if case_id not in cases:
            raise InputError(f"{row['_source']}: unknown case_id {case_id}")
        key = (case_id, finding_id)
        if key in seen:
            raise InputError(f"{row['_source']}: duplicate finding_id {finding_id} in {case_id}")
        seen.add(key)
        classification = row.get("classification")
        if classification not in CLASSIFICATIONS:
            raise InputError(f"{row['_source']}: invalid classification {classification!r}")
        disposition = row.get("disposition")
        if disposition not in DISPOSITIONS:
            raise InputError(f"{row['_source']}: invalid disposition {disposition!r}")
        gold_ids = row.get("gold_bug_ids")
        if not isinstance(gold_ids, list) or any(not isinstance(item, str) for item in gold_ids):
            raise InputError(f"{row['_source']}: gold_bug_ids must be a list of strings")
        unknown = set(gold_ids) - cases[case_id]["gold_ids"]
        if unknown:
            raise InputError(f"{row['_source']}: unknown gold ids {sorted(unknown)}")
        if classification == "bug_hit" and not gold_ids:
            raise InputError(f"{row['_source']}: bug_hit requires at least one gold id")
        if classification != "bug_hit" and gold_ids:
            raise InputError(f"{row['_source']}: only bug_hit can reference gold ids")
    return judgments


def ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def score_subset(
    case_ids: set[str], cases: dict[str, dict[str, Any]], judgments: list[dict[str, Any]]
) -> dict[str, Any]:
    selected = [row for row in judgments if row["case_id"] in case_ids]
    gold = {(case_id, gold_id) for case_id in case_ids for gold_id in cases[case_id]["gold_ids"]}
    hit_gold = {
        (row["case_id"], gold_id)
        for row in selected
        if row["classification"] == "bug_hit"
        for gold_id in row["gold_bug_ids"]
    }
    counts = Counter(row["classification"] for row in selected)
    dispositions = Counter(row["disposition"] for row in selected)
    finding_count = len(selected)
    useful_count = counts["bug_hit"] + counts["valid_suggestion"]
    noise_count = counts["noise"]
    return {
        "case_count": len(case_ids),
        "gold_bug_count": len(gold),
        "hit_gold_bug_count": len(hit_gold),
        "finding_count": finding_count,
        "bug_hit_count": counts["bug_hit"],
        "valid_suggestion_count": counts["valid_suggestion"],
        "useful_finding_count": useful_count,
        "false_positive_count": noise_count,
        "recall": ratio(len(hit_gold), len(gold)),
        "precision": ratio(counts["bug_hit"], finding_count),
        "usefulness": ratio(useful_count, finding_count),
        "false_positive_rate": ratio(noise_count, finding_count),
        "signal_to_noise": ratio(useful_count, noise_count),
        "dispositions": {name: dispositions[name] for name in sorted(DISPOSITIONS)},
    }


def metric_deltas(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, float | None]:
    deltas: dict[str, float | None] = {}
    for name in METRIC_NAMES:
        current_value = current.get(name)
        baseline_value = baseline.get(name)
        if isinstance(current_value, (int, float)) and isinstance(baseline_value, (int, float)):
            deltas[name] = round(current_value - baseline_value, 6)
        else:
            deltas[name] = None
    return deltas


def build_report(
    cases: dict[str, dict[str, Any]], judgments: list[dict[str, Any]], baseline: dict[str, Any] | None
) -> dict[str, Any]:
    aggregate = score_subset(set(cases), cases, judgments)
    benchmark_cases: dict[str, set[str]] = defaultdict(set)
    for case_id, case in cases.items():
        benchmark_cases[case["benchmark"]].add(case_id)
    report: dict[str, Any] = {
        "schema_version": 1,
        "aggregate": aggregate,
        "by_benchmark": {
            benchmark: score_subset(case_ids, cases, judgments)
            for benchmark, case_ids in sorted(benchmark_cases.items())
        },
    }
    if baseline is not None:
        baseline_aggregate = baseline.get("aggregate", baseline)
        if not isinstance(baseline_aggregate, dict):
            raise InputError("The baseline report must contain an aggregate object")
        report["delta_from_baseline"] = metric_deltas(aggregate, baseline_aggregate)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="+", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--baseline-report", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        cases = load_cases(args.cases)
        judgments = load_judgments(args.judgments, cases)
        baseline = None
        if args.baseline_report:
            with args.baseline_report.open(encoding="utf-8") as handle:
                baseline = json.load(handle)
        report = build_report(cases, judgments, baseline)
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
