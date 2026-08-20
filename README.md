# detailed-code-review

Tools for reviewing code so that somebody can decide whether it should merge.

Not so that a review looks thorough. Length and confidence do not prove that a finding is real.

The goal is useful defects found, noise removed, and uncertainty left visible.

## What is here

**`detailed-code-review`**, a skill for Codex and Claude Code. It reviews diffs, commits, and pull requests for concrete regressions.

**A review evaluator**, which measures recall, precision, usefulness, false positives, signal-to-noise, and finding dispositions.

**Two discovery checks**, which test whether the skill fires for review and stays quiet for implementation.

**A public benchmark design**, which compares the same model with and without the skill.

The skill is the product. The evaluator checks its results. Neither one proves the other works.

## Install

For Claude Code:

    /plugin marketplace add 0xfauzi/detailed-code-review
    /plugin install detailed-code-review@detailed-code-review

Use the skill:

    /detailed-code-review:detailed-code-review

For Codex, ask it to install this skill path:

    https://github.com/0xfauzi/detailed-code-review/tree/main/skills/detailed-code-review

Then request a review with `$detailed-code-review`.

## The skill, in one screen

1. **Fix the comparison range first.** Resolve exact base, head, and merge-base revisions before reading the diff.
2. **Map the change before judging lines.** Trace data, control, state, callers, consumers, and external effects.
3. **Require a real failure path.** Every finding needs a trigger, an observable result, and repository evidence.
4. **Route review lanes before inspection.** Use independent specialists for distinct risks, then synthesize their evidence.
5. **Show what was covered.** Record reviewed, irrelevant, uncovered, and defective risk areas.
6. **Give one merge verdict.** Choose `Block`, `Request changes`, `Discuss`, `Approve with follow-up`, or `Approve`.
7. **Keep the history.** Track accepted, rejected, disputed, fixed, deferred, and open findings by stable identifier.

The skill reviews without editing unless the user also requests fixes.

`skills/detailed-code-review/SKILL.md` is the procedure. Its `references/` directory holds the protocol, checks, and evaluation format.

## About measurement, honestly

We cannot measure this skill by asking whether its output sounds like a good review.

A finding either matches a real defect, identifies another useful issue, or creates noise. Those labels still require judgment.

The included smoke fixtures test the scoring arithmetic. They contain synthetic labels and say nothing about model review quality.

The closest test is paired evaluation on real pull requests. It measures first-round P1 recall, late discovery, noise, and cost.

That benchmark has not run yet. `research/results.md` says so plainly instead of presenting smoke values as product results.

`evals/README.md` explains each available measurement and its limits. `research/benchmark-design.md` fixes the public comparison before scores exist.

Run the repository validation:

    uv run python scripts/validate_repository.py

Run the Claude Code discovery checks when your account supports plugin evals:

    claude plugin eval .

## Licence

MIT. See `LICENSE`.
