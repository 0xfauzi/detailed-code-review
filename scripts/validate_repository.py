#!/usr/bin/env python3
"""Validate the public skill repository and its deterministic smoke evaluation."""

from __future__ import annotations

import json
import subprocess
import sys
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
    if not isinstance(marketplace, dict) or marketplace.get("name") != "detailed-code-review":
        fail("marketplace.json has the wrong name")


def validate_required_files() -> None:
    required = [
        ROOT / "README.md",
        ROOT / "LICENSE",
        ROOT / "evals" / "README.md",
        ROOT / "research" / "benchmark-design.md",
        ROOT / "research" / "results.md",
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


def main() -> int:
    try:
        validate_metadata()
        validate_required_files()
        validate_smoke_evaluation()
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
