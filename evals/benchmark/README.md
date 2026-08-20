# Live benchmark pilot

This pilot measures review outcomes on two frozen Code Review Bench cases.

It compares four Claude Code conditions with one model and one prompt:

1. `single_no_skill` disables skills and the `Agent` tool.
2. `single_with_skill` loads this skill and disables the `Agent` tool.
3. `adaptive_swarm` loads this skill and enables the `Agent` tool.
4. `forced_swarm` requires the skill and independent specialist delegation.

The first comparison measures the skill procedure without delegation.

The second comparison measures adaptive delegation against local review lanes.

Raw `subagent_stats` determine whether a swarm condition actually delegated.

This pilot does not match token budgets. It publishes measured token use and cost instead.

## Reproduce

Run a parser-only dry run first:

```bash
uv run python evals/benchmark/run_pilot.py run --dry-run
```

Run live reviewers:

```bash
uv run python evals/benchmark/run_pilot.py run
```

Run the blinded judge:

```bash
uv run python evals/benchmark/run_pilot.py judge
```

Build the evaluator report:

```bash
uv run python evals/benchmark/run_pilot.py report
```

The harness verifies every base revision, target revision, merge base, and diff digest.

It rejects working-tree changes after each review.

## Interpretation

This is a pipeline pilot. It is not a leaderboard result.

The pilot added its multi-P1 case and forced condition after earlier results were visible.

Treat every comparison as exploratory.

One replicate cannot measure stochastic variance. Two cases cannot support general performance claims.

The official Code Review Bench judge is not used. The pilot uses a blinded Claude judge.

Code Review Bench uses an MIT-licensed fixed dataset. Its static cases can have training contamination.

See `results/pilot-v1/RESULTS.md` for measured results and validity limits.
