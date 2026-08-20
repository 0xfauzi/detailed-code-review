# Results

## Current status

No public model-quality benchmark has completed.

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

## Publication rule

Do not describe the smoke values as benchmark results.

Add model-quality results only after completing the paired design in `benchmark-design.md`.

Publish raw outputs, judge outputs, configuration, failures, and aggregate reports together.
