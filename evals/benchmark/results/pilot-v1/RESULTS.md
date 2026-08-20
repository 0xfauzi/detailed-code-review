# Code Review Bench pilot results

This pilot used two frozen Code Review Bench cases with six gold findings.

Four gold findings have `P1` priority. Two have `P3` priority.

The pilot ran one replicate for each condition and case.

## Results

| Condition | Subagents | P1 recall, micro | P1 recall, macro | All recall, micro | All recall, macro | Usefulness | Noise | Cost | Wall time | Processed tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `single_no_skill` | 0 | 1.000000 | 1.000000 | 0.666667 | 0.625000 | 0.909091 | 0.090909 | $2.235060 | 429.258347s | 2,606,959 |
| `single_with_skill` | 0 | 0.500000 | 0.666667 | 0.500000 | 0.625000 | 1.000000 | 0.000000 | $2.743811 | 420.952841s | 4,408,594 |
| `adaptive_swarm` | 0 | 1.000000 | 1.000000 | 0.833333 | 0.875000 | 1.000000 | 0.000000 | $2.487743 | 413.748621s | 3,134,601 |
| `forced_swarm` | 4 | 1.000000 | 1.000000 | 0.666667 | 0.625000 | 0.909091 | 0.090909 | $8.287826 | 1129.641876s | 12,860,843 |

Processed tokens include input, output, cache creation, and cache reads across every model session.

The `adaptive_swarm` configuration made delegation available. Claude Code spawned no subagents.

Therefore, that row does not measure a swarm. It measures adaptive routing that stayed local.

The `forced_swarm` configuration spawned two specialists per case. All four specialists completed.

## Primary comparison

The forced swarm recovered the local skill condition's escaped P1 findings.

- Micro P1 recall increased by `0.500000`.
- Paired macro P1 recall increased by `0.333334`.
- Micro all-priority recall increased by `0.166667`.
- Macro all-priority recall did not change.
- Noise increased by `0.090909`.
- Usefulness decreased by `0.090909`.
- Cost increased by `3.020553x`.
- Processed tokens increased by `2.917221x`.
- Wall time increased by `2.683535x`.

The forced swarm matched the no-skill control on every quality metric.

It cost `3.708100x` more and took `2.631613x` longer than that control.

This pilot does not show that the skill beats a generic reviewer.

It does show that forced specialists removed the local skill condition's first-round P1 escapes.

## Frozen configuration

- Dataset: Code Review Bench offline commit `2b092b670f7d6cae6d429babaaee18948b4bdacb`.
- Cases: `crb-discourse-002` and `crb-sentry-001`.
- Reviewer: Claude Code `2.1.238`.
- Reviewer model: `claude-sonnet-5` with observed `claude-haiku-4-5-20251001` support calls.
- Judge model: `claude-opus-5`.
- Skill revision: `b4039fa`.
- Effort: `high`.
- Replicates: one.
- Review cost: `$15.754440`.
- Judge cost: `$0.470087`.

Code Review Bench `High` severity maps to `P1`. `Low` severity maps to `P3`.

## Validity limits

- Two cases cannot support a general performance claim.
- One replicate cannot measure stochastic variance.
- Conditions did not use matched token budgets.
- The official Code Review Bench judge was unavailable.
- A blinded Claude judge matched findings against human gold comments.
- The static dataset can have training contamination.
- Off-gold valid suggestions depend on judge accuracy.
- The forced swarm used a condition-specific system instruction.
- Cases were deliberately selected instead of randomly sampled.
- The multi-P1 case was selected after the first case completed.
- The forced condition was added after telemetry showed zero adaptive delegation.

These post-hoc pilot changes make every comparison exploratory.

Treat these values as pilot results. Do not present them as leaderboard scores.
