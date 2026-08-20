#!/usr/bin/env python3
"""Run, judge, and score the frozen Code Review Bench pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "evals" / "benchmark"
CONFIG_PATH = BENCHMARK / "configs" / "pilot-v1.json"
CASES_PATH = BENCHMARK / "cases" / "pilot-v1.jsonl"
REVIEW_SCHEMA = BENCHMARK / "schemas" / "review-output.schema.json"
JUDGE_SCHEMA = BENCHMARK / "schemas" / "judge-output.schema.json"
RESULTS = BENCHMARK / "results" / "pilot-v1"
SKILL_REVISION = "b4039fa"


class PilotError(RuntimeError):
    """Raised when a benchmark invariant fails."""


def run_command(
    args: list[str], cwd: Path, *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, check=False
    )
    if check and completed.returncode != 0:
        raise PilotError(f"Command failed: {' '.join(args)}\n{completed.stderr}")
    return completed


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PilotError(f"{path} must contain an object")
    return value


def load_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line
    ]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def merge_jsonl(path: Path, rows: list[dict[str, Any]], key: str) -> None:
    existing: list[dict[str, Any]] = []
    if path.is_file():
        existing = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line
        ]
    merged = {row[key]: row for row in existing}
    merged.update({row[key]: row for row in rows})
    write_jsonl(path, [merged[item] for item in sorted(merged)])


def git(repo: Path, *args: str) -> str:
    return run_command(["git", *args], repo).stdout.strip()


def frozen_diff(repo: Path, base_revision: str, target_revision: str) -> str:
    return run_command(
        [
            "git",
            "-c",
            "core.abbrev=40",
            "diff",
            "--full-index",
            "--binary",
            "--no-ext-diff",
            "--no-textconv",
            f"{base_revision}...{target_revision}",
        ],
        repo,
    ).stdout


def prepare_case(case: dict[str, Any], work_root: Path) -> Path:
    repo = work_root / case.get("workspace_name", case["case_id"])
    if not (repo / ".git").is_dir():
        repo.parent.mkdir(parents=True, exist_ok=True)
        run_command(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                case["repo_url"],
                str(repo),
            ],
            repo.parent,
        )
    run_command(
        ["git", "fetch", "--deepen=100", "origin", case["base_ref"], case["head_ref"]],
        repo,
    )
    git(repo, "checkout", "--detach", case["target_revision"])
    if git(repo, "rev-parse", "HEAD") != case["target_revision"]:
        raise PilotError(f"{case['case_id']}: target revision mismatch")
    if (
        git(repo, "merge-base", case["base_revision"], case["target_revision"])
        != case["base_revision"]
    ):
        raise PilotError(f"{case['case_id']}: base is not the merge base")
    diff = frozen_diff(repo, case["base_revision"], case["target_revision"])
    if hashlib.sha256(diff.encode()).hexdigest() != case["diff_sha256"]:
        raise PilotError(f"{case['case_id']}: diff digest mismatch")
    if git(repo, "status", "--short"):
        raise PilotError(f"{case['case_id']}: worktree is not clean")
    return repo


def review_prompt(case: dict[str, Any]) -> str:
    return (
        f"Review the exact Git change {case['base_revision']}...{case['target_revision']}. "
        "Do not edit files. Find concrete defects introduced by this change. "
        "Inspect affected unchanged code when needed. Return only the required structured output."
    )


def claude_result(command: list[str], cwd: Path) -> tuple[dict[str, Any], float]:
    started = time.monotonic()
    completed = run_command(command, cwd)
    elapsed = time.monotonic() - started
    payload = json.loads(completed.stdout)
    if payload.get("is_error"):
        raise PilotError(f"Claude returned an error: {payload}")
    if not isinstance(payload.get("structured_output"), dict):
        raise PilotError("Claude returned no structured_output")
    payload.pop("session_id", None)
    payload.pop("uuid", None)
    return payload, elapsed


def reviewer_command(
    case: dict[str, Any], condition: dict[str, Any], config: dict[str, Any]
) -> list[str]:
    tools = ["Bash", "Read", "Grep", "Glob"]
    if condition["skills_enabled"]:
        tools.append("Skill")
    if condition["agent_tool_enabled"]:
        tools.append("Agent")
    command = [
        "claude",
        "-p",
        review_prompt(case),
        "--model",
        config["model"],
        "--effort",
        config["effort"],
        "--output-format",
        "json",
        "--json-schema",
        REVIEW_SCHEMA.read_text(encoding="utf-8"),
        "--permission-mode",
        "dontAsk",
        "--setting-sources",
        "project",
        "--tools",
        ",".join(tools),
        "--no-session-persistence",
        "--no-chrome",
    ]
    if condition["skills_enabled"]:
        command.extend(["--plugin-dir", str(ROOT)])
    else:
        command.append("--disable-slash-commands")
    if condition.get("system_instruction"):
        command.extend(["--append-system-prompt", condition["system_instruction"]])
    return command


def token_count(payload: dict[str, Any]) -> int | None:
    model_usage = payload.get("modelUsage")
    if isinstance(model_usage, dict) and model_usage:
        fields = (
            "inputTokens",
            "cacheCreationInputTokens",
            "cacheReadInputTokens",
            "outputTokens",
        )
        values = [
            usage.get(field)
            for usage in model_usage.values()
            if isinstance(usage, dict)
            for field in fields
        ]
        if values and all(isinstance(value, int) for value in values):
            return sum(values)
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    fields = (
        "input_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "output_tokens",
    )
    values = [usage.get(field) for field in fields]
    return sum(values) if all(isinstance(value, int) for value in values) else None


def raw_filename(run_id: str) -> str:
    return run_id.replace("::", "__") + ".json"


def refresh_manifest_telemetry() -> None:
    path = RESULTS / "runs.jsonl"
    runs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for run in runs:
        raw_path = RESULTS / "raw" / raw_filename(run["run_id"])
        if not raw_path.is_file():
            continue
        payload = load_json(raw_path)
        subagents = payload.get("subagent_stats", {})
        run.update(
            token_count=token_count(payload),
            turn_count=payload.get("num_turns"),
            subagent_spawned=subagents.get("spawned"),
            subagent_completed=subagents.get("completed"),
        )
    write_jsonl(path, runs)


def run_reviews(
    dry_run: bool,
    work_root: Path,
    selected_case_ids: set[str],
    selected_conditions: set[str],
) -> None:
    config = load_json(CONFIG_PATH)
    manifest: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    cases = load_cases()
    if selected_case_ids:
        cases = [case for case in cases if case["case_id"] in selected_case_ids]
        missing = selected_case_ids - {case["case_id"] for case in cases}
        if missing:
            raise PilotError(f"Unknown case identifiers: {sorted(missing)}")
    conditions = config["conditions"]
    if selected_conditions:
        conditions = [
            item for item in conditions if item["name"] in selected_conditions
        ]
        missing = selected_conditions - {item["name"] for item in conditions}
        if missing:
            raise PilotError(f"Unknown conditions: {sorted(missing)}")
    for case in cases:
        repo = prepare_case(case, work_root)
        for condition in conditions:
            run_id = (
                f"{case['case_id']}::{condition['name']}::{config['replicate_id']}::1"
            )
            if dry_run:
                payload = {
                    "structured_output": {
                        "findings": [],
                        "verdict": "Approve",
                        "coverage": ["dry-run"],
                        "validation_gaps": [],
                    },
                    "usage": {
                        "input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "output_tokens": 0,
                    },
                    "total_cost_usd": 0,
                    "duration_ms": 0,
                    "modelUsage": {},
                }
                elapsed = 0.0
            else:
                payload, elapsed = claude_result(
                    reviewer_command(case, condition, config), repo
                )
            if git(repo, "status", "--short"):
                raise PilotError(f"{run_id}: reviewer changed the worktree")
            write_json(RESULTS / "raw" / raw_filename(run_id), payload)
            output = payload["structured_output"]
            outputs.append({"run_id": run_id, "case_id": case["case_id"], **output})
            models = sorted(payload.get("modelUsage", {}))
            subagents = payload.get("subagent_stats", {})
            manifest.append(
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "case_id": case["case_id"],
                    "condition": condition["name"],
                    "replicate_id": config["replicate_id"],
                    "round": 1,
                    "status": "complete",
                    "repository": case["repository"],
                    "base_revision": case["base_revision"],
                    "target_revision": case["target_revision"],
                    "diff_sha256": case["diff_sha256"],
                    "model": models[0] if len(models) == 1 else models,
                    "agent": "claude-code",
                    "agent_version": run_command(
                        ["claude", "--version"], repo
                    ).stdout.strip(),
                    "skill_revision": SKILL_REVISION
                    if condition["skills_enabled"]
                    else None,
                    "token_count": token_count(payload),
                    "tool_call_count": None,
                    "turn_count": payload.get("num_turns"),
                    "subagent_spawned": subagents.get("spawned"),
                    "subagent_completed": subagents.get("completed"),
                    "wall_time_seconds": round(elapsed, 6),
                    "cost_usd": payload.get("total_cost_usd"),
                }
            )
    merge_jsonl(RESULTS / "runs.jsonl", manifest, "run_id")
    merge_jsonl(RESULTS / "review-outputs.jsonl", outputs, "run_id")


def judge_prompt(cases: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> str:
    gold = {
        case["case_id"]: [
            {"id": item["id"], "comment": item["comment"]}
            for item in case["gold_findings"]
        ]
        for case in cases
    }
    return (
        "Judge code-review candidates against human gold comments. Condition names are hidden. "
        "Use bug_hit only for the same underlying issue. Use valid_suggestion for another concrete, "
        "actionable defect. Use noise for unsupported or non-actionable claims. A bug_hit needs at "
        "least one gold_bug_id. Other classes need none. Return one judgment for every candidate.\n\n"
        + json.dumps({"gold": gold, "candidates": candidates}, sort_keys=True)
    )


def judge_results() -> None:
    config = load_json(CONFIG_PATH)
    cases = load_cases()
    outputs = [
        json.loads(line)
        for line in (RESULTS / "review-outputs.jsonl").read_text().splitlines()
    ]
    candidates: list[dict[str, Any]] = []
    mapping: dict[str, tuple[dict[str, Any], int]] = {}
    for output in outputs:
        for index, finding in enumerate(output["findings"], 1):
            candidate_id = hashlib.sha256(
                f"{output['run_id']}::{index}".encode()
            ).hexdigest()[:16]
            candidates.append(
                {"candidate_id": candidate_id, "case_id": output["case_id"], **finding}
            )
            mapping[candidate_id] = (output, index)
    if not candidates:
        write_json(
            RESULTS / "judge-raw.json",
            {"dry_run": True, "structured_output": {"judgments": []}},
        )
        write_jsonl(RESULTS / "judgments.jsonl", [])
        return
    random.Random(config["random_seed"]).shuffle(candidates)
    batch_dir = RESULTS / "judge-batches"
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_payloads = [load_json(path) for path in sorted(batch_dir.glob("*.json"))]
    by_id = {
        item["candidate_id"]: item
        for payload in batch_payloads
        for item in payload["structured_output"]["judgments"]
        if item["candidate_id"] in mapping
    }
    missing_candidates = [
        item for item in candidates if item["candidate_id"] not in by_id
    ]
    if missing_candidates:
        command = [
            "claude",
            "-p",
            judge_prompt(cases, missing_candidates),
            "--model",
            config["judge_model"],
            "--effort",
            config["effort"],
            "--output-format",
            "json",
            "--json-schema",
            JUDGE_SCHEMA.read_text(encoding="utf-8"),
            "--tools",
            "",
            "--disable-slash-commands",
            "--no-session-persistence",
            "--no-chrome",
        ]
        payload, _ = claude_result(command, ROOT)
        batch_name = hashlib.sha256(
            "\n".join(
                sorted(item["candidate_id"] for item in missing_candidates)
            ).encode()
        ).hexdigest()[:16]
        write_json(batch_dir / f"batch-{batch_name}.json", payload)
        batch_payloads.append(payload)
        by_id.update(
            {
                item["candidate_id"]: item
                for item in payload["structured_output"]["judgments"]
            }
        )
    if set(by_id) != set(mapping):
        raise PilotError(
            "Judge candidate identifiers do not match after incremental judging"
        )
    write_json(
        RESULTS / "judge-raw.json",
        {
            "batch_count": len(batch_payloads),
            "structured_output": {"judgments": [by_id[item] for item in sorted(by_id)]},
        },
    )
    rows: list[dict[str, Any]] = []
    for candidate_id, (output, index) in mapping.items():
        finding = output["findings"][index - 1]
        judgment = by_id[candidate_id]
        rows.append(
            {
                "run_id": output["run_id"],
                "case_id": output["case_id"],
                "agent_role": "reviewer",
                "finding_id": f"F{index}",
                "classification": judgment["classification"],
                "gold_bug_ids": judgment["gold_bug_ids"],
                "predicted_priority": finding["priority"],
                "disposition": "open",
                "reason": judgment["reason"],
            }
        )
    write_jsonl(RESULTS / "judgments.jsonl", rows)


def evaluator_cases() -> list[dict[str, Any]]:
    rows = []
    for case in load_cases():
        work_root = Path("work/benchmarks/fixtures")
        repo = ROOT.parents[1] / work_root / case.get("workspace_name", case["case_id"])
        diff = frozen_diff(repo, case["base_revision"], case["target_revision"])
        rows.append(
            {
                "schema_version": 1,
                "benchmark": case["benchmark"],
                "fixture_kind": case["fixture_kind"],
                "case_id": case["case_id"],
                "repository": case["repository"],
                "base_revision": case["base_revision"],
                "target_revision": case["target_revision"],
                "diff_sha256": case["diff_sha256"],
                "title": case["title"],
                "description": "Frozen Code Review Bench case.",
                "diff": diff,
                "gold_findings": case["gold_findings"],
            }
        )
    return rows


def build_report() -> None:
    refresh_manifest_telemetry()
    cases = RESULTS / "evaluator-cases.jsonl"
    write_jsonl(cases, evaluator_cases())
    evaluator = (
        ROOT / "skills" / "detailed-code-review" / "scripts" / "evaluate_reviews.py"
    )
    completed = run_command(
        [
            sys.executable,
            str(evaluator),
            "--cases",
            str(cases),
            "--runs",
            str(RESULTS / "runs.jsonl"),
            "--judgments",
            str(RESULTS / "judgments.jsonl"),
        ],
        ROOT,
    )
    report = json.loads(completed.stdout)
    write_json(RESULTS / "report.json", report)
    comparisons = (
        ("single_with_skill", "forced_swarm", "forced-vs-local.json"),
        ("single_no_skill", "forced_swarm", "forced-vs-control.json"),
        ("single_with_skill", "adaptive_swarm", "adaptive-vs-local.json"),
    )
    for control, treatment, filename in comparisons:
        completed = run_command(
            [
                sys.executable,
                str(evaluator),
                "--cases",
                str(cases),
                "--runs",
                str(RESULTS / "runs.jsonl"),
                "--judgments",
                str(RESULTS / "judgments.jsonl"),
                "--control-condition",
                control,
                "--treatment-condition",
                treatment,
            ],
            ROOT,
        )
        write_json(RESULTS / "comparisons" / filename, json.loads(completed.stdout))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--case-id", action="append", default=[])
    run_parser.add_argument("--condition", action="append", default=[])
    run_parser.add_argument(
        "--work-root",
        type=Path,
        default=ROOT.parents[1] / "work" / "benchmarks" / "fixtures",
    )
    subparsers.add_parser("judge")
    subparsers.add_parser("report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "run":
            run_reviews(
                args.dry_run,
                args.work_root,
                set(args.case_id),
                set(args.condition),
            )
        elif args.command == "judge":
            judge_results()
        else:
            build_report()
    except (OSError, ValueError, PilotError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
