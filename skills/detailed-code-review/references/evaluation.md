# Review Evaluation

Use evaluation to measure review behavior across repeatable cases. Run the smoke fixtures before a larger benchmark.

## Fixture Format

Store one JSON object per line. Each case uses these fields:

- `schema_version`: Integer schema version. Use `1`.
- `benchmark`: Dataset or suite name.
- `fixture_kind`: Use `synthetic_smoke` or `benchmark_export`.
- `case_id`: Stable case identifier.
- `repository`: Repository identifier or local path.
- `base_revision`: Exact base revision.
- `target_revision`: Exact target revision.
- `title`: Short change title.
- `description`: Intended behavior and relevant constraints.
- `diff`: Review diff or a path supplied by the evaluation harness.
- `gold_findings`: Objects with stable `id`, `summary`, and `priority` fields.

The included CR-Bench and c-CRAB files are synthetic smoke fixtures. They test the evaluation pipeline only.

For a CR-Bench export, preserve each gold defect identifier. Add human judgments for every generated finding.

For a c-CRAB export, preserve `instance_id` as `case_id`. Preserve exact base and head commits.

Keep executable c-CRAB resolution results separate from comment-quality labels. Both signals answer different questions.

## Judgment Format

Store one JSON object per generated finding. Use these fields:

- `case_id`: Fixture case identifier.
- `finding_id`: Stable generated finding identifier.
- `classification`: `bug_hit`, `valid_suggestion`, or `noise`.
- `gold_bug_ids`: Gold identifiers matched by this finding.
- `disposition`: `open`, `accepted`, `rejected`, `disputed`, `fixed`, or `deferred`.
- `reason`: Short evidence-based classification reason.

A `bug_hit` must reference at least one gold identifier. Other classifications must not reference gold identifiers.

## Metrics

Run:

`uv run python scripts/evaluate_reviews.py --cases fixtures/cr-bench-smoke.jsonl fixtures/c-crab-smoke.jsonl --judgments fixtures/smoke-judgments.jsonl`

The evaluator reports aggregate and per-benchmark metrics:

- Recall: Unique gold defects hit divided by all gold defects.
- Precision: `bug_hit` comments divided by all generated comments.
- Usefulness: `bug_hit` and `valid_suggestion` comments divided by all comments.
- False positives: Comments classified as `noise`.
- False-positive rate: Noise comments divided by all comments.
- Signal-to-noise ratio: Useful comments divided by noise comments.

The false-positive rate is comment-level noise. It is not a statistical rate over true negatives.

The signal-to-noise ratio is `null` when no noise exists. Do not replace that result with an invented value.

Use `--baseline-report <report.json>` to show metric deltas. The evaluator does not invent pass thresholds.

## Evaluation Process

1. Run the synthetic smoke fixtures.
2. Confirm that the generated report matches `fixtures/smoke-expected.json`.
3. Normalize licensed benchmark exports to the fixture format.
4. Run the same reviewer configuration more than once when nondeterminism matters.
5. Record the model, prompt or skill revision, tools, repository state, and runtime limits.
6. Compare metrics and inspect false positives manually.
7. Keep behavioral c-CRAB pass results beside comment-quality metrics.

Do not tune only for recall. Increased recall can reduce usefulness and increase noise.
