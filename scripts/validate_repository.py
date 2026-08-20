#!/usr/bin/env python3
"""Validate the public skill repository and its deterministic smoke evaluation."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "detailed-code-review"


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{path.relative_to(ROOT)}: {error}")


def validate_metadata() -> None:
    skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    if not skill_text.startswith("---\n"):
        fail("SKILL.md has no YAML frontmatter")
    frontmatter = skill_text.split("---\n", 2)[1]
    if "name: detailed-code-review" not in frontmatter:
        fail("SKILL.md has the wrong name")
    if "description:" not in frontmatter:
        fail("SKILL.md has no description")

    plugin = load_json(ROOT / ".claude-plugin" / "plugin.json")
    if not isinstance(plugin, dict) or plugin.get("name") != "detailed-code-review":
        fail("plugin.json has the wrong name")
    if plugin.get("skills") != ["./skills/detailed-code-review"]:
        fail("plugin.json has the wrong skill path")

    marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    if (
        not isinstance(marketplace, dict)
        or marketplace.get("name") != "detailed-code-review"
    ):
        fail("marketplace.json has the wrong name")


def validate_required_files() -> None:
    required = [
        ROOT / "README.md",
        ROOT / "LICENSE",
        ROOT / "evals" / "README.md",
        ROOT / "research" / "benchmark-design.md",
        ROOT / "research" / "results.md",
        ROOT / "evals" / "benchmark" / "README.md",
        ROOT / "evals" / "benchmark" / "NOTICE.md",
        ROOT / "evals" / "benchmark" / "run_pilot.py",
        ROOT / "evals" / "benchmark" / "results" / "pilot-v1" / "RESULTS.md",
        ROOT / "evals" / "benchmark" / "results" / "pilot-v1" / "report.json",
        ROOT
        / "evals"
        / "benchmark"
        / "results"
        / "pilot-v1"
        / "comparisons"
        / "forced-vs-local.json",
        SKILL / "references" / "multi-agent-review.md",
        SKILL / "fixtures" / "multi-round-cases.jsonl",
        SKILL / "fixtures" / "multi-round-runs.jsonl",
        SKILL / "fixtures" / "multi-round-judgments.jsonl",
        SKILL / "fixtures" / "multi-round-expected.json",
        ROOT / "evals" / "fires-on-review" / "prompt.md",
        ROOT / "evals" / "fires-on-review" / "graders" / "skill-fired.md",
        ROOT / "evals" / "stays-out-of-implementation" / "prompt.md",
        ROOT
        / "evals"
        / "stays-out-of-implementation"
        / "graders"
        / "skill-stays-quiet.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        fail(f"Missing required files: {', '.join(missing)}")


def validate_smoke_evaluation() -> None:
    evaluator = SKILL / "scripts" / "evaluate_reviews.py"
    cases = [
        SKILL / "fixtures" / "cr-bench-smoke.jsonl",
        SKILL / "fixtures" / "c-crab-smoke.jsonl",
    ]
    judgments = SKILL / "fixtures" / "smoke-judgments.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            str(evaluator),
            "--cases",
            *(str(path) for path in cases),
            "--judgments",
            str(judgments),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)
    expected = load_json(SKILL / "fixtures" / "smoke-expected.json")
    if not isinstance(expected, dict):
        fail("smoke-expected.json must contain an object")
    aggregate = report.get("aggregate", {})
    measured = {name: aggregate.get(name) for name in expected}
    if measured != expected:
        fail(f"Smoke metrics differ: measured={measured}, expected={expected}")


def validate_multi_round_evaluation() -> None:
    evaluator = SKILL / "scripts" / "evaluate_reviews.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(evaluator),
            "--cases",
            str(SKILL / "fixtures" / "multi-round-cases.jsonl"),
            "--runs",
            str(SKILL / "fixtures" / "multi-round-runs.jsonl"),
            "--judgments",
            str(SKILL / "fixtures" / "multi-round-judgments.jsonl"),
            "--control-condition",
            "single",
            "--treatment-condition",
            "adaptive_swarm",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)
    expected = load_json(SKILL / "fixtures" / "multi-round-expected.json")
    if not isinstance(expected, dict):
        fail("multi-round-expected.json must contain an object")
    measured = {
        "single": {
            name: report["by_condition"]["single"].get(name)
            for name in expected["single"]
        },
        "adaptive_swarm": {
            name: report["by_condition"]["adaptive_swarm"].get(name)
            for name in expected["adaptive_swarm"]
        },
        "comparison": {
            name: report["condition_comparison"].get(name)
            for name in expected["comparison"]
        },
    }
    if measured != expected:
        fail(f"Multi-round metrics differ: measured={measured}, expected={expected}")
    if report.get("run_mode") != "explicit":
        fail("Multi-round evaluation did not use explicit runs")
    if report.get("run_statuses", {}).get("complete") != 4:
        fail("Multi-round evaluation did not retain every completed run")
    if (
        report["by_condition"]["adaptive_swarm"]["rounds"]["2"]["raw_finding_count"]
        != 0
    ):
        fail("Multi-round evaluation did not retain the zero-finding round")
    provenance = report.get("case_provenance", {}).get("rounds-smoke-001", {})
    if (
        provenance.get("diff_sha256")
        != "28b1323b268724dc748e45e0f115e110232ce553e2860ee3c7365dabc696411c"
    ):
        fail("Multi-round evaluation lost revision provenance")
    comparison = report["condition_comparison"]
    if comparison.get("token_ratio") != 1.0 or comparison.get("cost_ratio") != 1.0:
        fail("Multi-round evaluation calculated the wrong resource ratio")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def run_evaluator(runs: Path, judgments: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "evaluate_reviews.py"),
            "--cases",
            str(SKILL / "fixtures" / "multi-round-cases.jsonl"),
            "--runs",
            str(runs),
            "--judgments",
            str(judgments),
        ],
        capture_output=True,
        check=False,
        text=True,
    )


def validate_run_and_duplicate_failures() -> None:
    base_run = json.loads(
        (SKILL / "fixtures" / "multi-round-runs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        judgments = temporary / "findings.jsonl"
        judgments.write_text("", encoding="utf-8")

        complete = {**base_run, "run_id": "complete", "condition": "mixed"}
        failed = {
            **base_run,
            "run_id": "failed",
            "condition": "mixed",
            "replicate_id": "rep-2",
            "status": "failed",
        }
        not_run = {
            **base_run,
            "run_id": "not-run",
            "condition": "unstarted",
            "status": "not_run",
        }
        runs = temporary / "runs.jsonl"
        write_jsonl(runs, [complete, failed, not_run])
        result = run_evaluator(runs, judgments)
        if result.returncode != 0:
            fail(f"Run-state fixture failed: {result.stderr.strip()}")
        report = json.loads(result.stdout)
        if report["by_condition"]["mixed"]["review_unit_count"] != 1:
            fail("A failed replicate changed the completed review-unit count")
        if report["by_condition"]["mixed"]["p1_gold_count"] != 2:
            fail("A failed replicate was scored as missed gold")
        if report["run_statuses"] != {"complete": 1, "failed": 1, "not_run": 1}:
            fail("Run statuses were not retained")

        mismatched = {**complete, "diff_sha256": "0" * 64}
        write_jsonl(runs, [mismatched])
        if run_evaluator(runs, judgments).returncode == 0:
            fail("A mismatched revision was accepted")

        write_jsonl(runs, [complete])
        first = {
            "run_id": "complete",
            "case_id": "rounds-smoke-001",
            "finding_id": "F1",
            "classification": "bug_hit",
            "gold_bug_ids": ["G1"],
            "duplicate_of": "F2",
            "disposition": "accepted",
            "reason": "Cycle member one.",
        }
        second = {
            **first,
            "finding_id": "F2",
            "gold_bug_ids": ["G2"],
            "duplicate_of": "F1",
            "reason": "Cycle member two.",
        }
        write_jsonl(judgments, [first, second])
        if run_evaluator(runs, judgments).returncode == 0:
            fail("A cyclic duplicate graph was accepted")


def validate_live_pilot_artifacts() -> None:
    pilot = ROOT / "evals" / "benchmark" / "results" / "pilot-v1"
    runs_path = pilot / "runs.jsonl"
    judgments_path = pilot / "judgments.jsonl"
    cases_path = pilot / "evaluator-cases.jsonl"
    report_path = pilot / "report.json"
    runs = [
        json.loads(line) for line in runs_path.read_text(encoding="utf-8").splitlines()
    ]
    if len(runs) != 8 or any(run.get("status") != "complete" for run in runs):
        fail("The live pilot must contain eight completed reviewer runs")
    forced = [run for run in runs if run.get("condition") == "forced_swarm"]
    if len(forced) != 2 or sum(run.get("subagent_completed", 0) for run in forced) != 4:
        fail("The forced swarm did not retain four completed specialists")
    adaptive = [run for run in runs if run.get("condition") == "adaptive_swarm"]
    if any(run.get("subagent_spawned") != 0 for run in adaptive):
        fail("The adaptive condition no longer records zero spawned specialists")
    completed = subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "evaluate_reviews.py"),
            "--cases",
            str(cases_path),
            "--runs",
            str(runs_path),
            "--judgments",
            str(judgments_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    measured = json.loads(completed.stdout)
    expected = load_json(report_path)
    if measured != expected:
        fail("The checked-in live pilot report does not match its raw artifacts")
    conditions = measured.get("by_condition", {})
    if conditions.get("forced_swarm", {}).get("first_round_p1_recall") != 1.0:
        fail("The forced-swarm pilot P1 recall changed")
    if conditions.get("single_with_skill", {}).get("first_round_p1_recall") != 0.5:
        fail("The local-skill pilot P1 recall changed")


def main() -> int:
    try:
        validate_metadata()
        validate_required_files()
        validate_smoke_evaluation()
        validate_multi_round_evaluation()
        validate_run_and_duplicate_failures()
        validate_live_pilot_artifacts()
    except (
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
