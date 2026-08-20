# Results

## Current status

No full public model-quality benchmark has completed.

A two-case live pilot has completed.

The repository includes synthetic fixtures that validate the scoring pipeline.

These fixtures do not measure the skill's review quality.

## Evaluator smoke test

The fixed smoke input contains two synthetic cases and four judged findings.

| Metric | Expected | Measured |
| --- | ---: | ---: |
| Gold defects | 3 | 3 |
| Gold defects hit | 2 | 2 |
| Recall | 0.666667 | 0.666667 |
| Precision | 0.500000 | 0.500000 |
| Usefulness | 0.750000 | 0.750000 |
| False-positive rate | 0.250000 | 0.250000 |
| Signal-to-noise ratio | 3.000000 | 3.000000 |

The repository validator compares measured values against the checked-in expected file.

## Multi-round evaluator smoke test

The second synthetic fixture checks round tracking, duplicate handling, and condition comparison.

| Metric | Single agent | Adaptive swarm |
| --- | ---: | ---: |
| First-round P1 recall | 0.500000 | 1.000000 |
| Late P1 rate | 0.500000 | 0.000000 |
| P1 saturation gap | 0.500000 | 0.000000 |
| Duplicate burden | 0.250000 | 0.000000 |
| Blocking recognition recall | 1.000000 | 0.500000 |

These values prove condition calculations against fixed labels. They are not model benchmark results.

## Publication rule

Do not describe the smoke values as benchmark results.

## Live Code Review Bench pilot

The repository now includes a live pilot on two frozen Code Review Bench cases.

The forced swarm spawned four specialists and reached `1.000000` micro P1 recall.

The local skill condition reached `0.500000` micro P1 recall.

The forced swarm cost `3.020553x` more than the local skill condition.

The no-skill control also reached `1.000000` micro P1 recall.

These results do not show that the skill beats a generic reviewer.

Read `evals/benchmark/results/pilot-v1/RESULTS.md` for raw metrics and validity limits.

Add model-quality results only after completing the paired design in `benchmark-design.md`.

Publish raw outputs, judge outputs, configuration, failures, and aggregate reports together.
