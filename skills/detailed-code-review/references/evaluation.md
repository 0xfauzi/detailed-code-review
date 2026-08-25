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
- `diff_sha256`: SHA-256 digest of the frozen review diff.
- `title`: Short change title.
- `description`: Intended behavior and relevant constraints.
- `diff`: Review diff or a path supplied by the evaluation harness.
- `gold_findings`: Objects with stable `id`, `summary`, and `priority` fields.

Gold findings may also include:

- `theme`: Review lane that owns the defect.
- `root_cause_id`: Stable root cause for symptom deduplication.
- `evidence_paths`: Files needed to validate the defect.
- `minimal_context`: Smallest contract or execution context needed to prove the defect.
- `present_in_initial_target`: Whether the defect existed in the frozen first-round revision. Defaults to `true`.

The included CR-Bench and c-CRAB files are synthetic smoke fixtures. They test the evaluation pipeline only.

For a CR-Bench export, preserve each gold defect identifier. Add human judgments for every generated finding.

For a c-CRAB export, preserve `instance_id` as `case_id`. Preserve exact base and head commits.

Keep executable c-CRAB resolution results separate from comment-quality labels. Both signals answer different questions.

## Run Format

Use a run manifest for multi-round, repeated, or comparative evaluation. Store one JSON object per scheduled round.

Each run record contains:

- `run_id`: Globally unique run identifier.
- `case_id`: Frozen fixture case.
- `condition`: Review configuration.
- `replicate_id`: Stable repetition identifier shared across paired conditions.
- `round`: Positive review round number.
- `status`: `complete`, `failed`, or `not_run`.
- `repository`, `base_revision`, `target_revision`, and `diff_sha256`: Values that must match the case.
- `model`, `agent`, and `skill_revision`: Frozen implementation identifiers.
- `token_count`, `tool_call_count`, `wall_time_seconds`, and `cost_usd`: Measured resource use when available.

Record failed and zero-finding runs. Do not represent run existence through findings.

Use an explicit run manifest for every public comparison. Legacy inferred runs support smoke checks only.

## Judgment Format

Store one JSON object per generated finding. Use these fields:

- `case_id`: Fixture case identifier.
- `run_id`: Run manifest identifier. Required when a run manifest is supplied.
- `finding_id`: Stable generated finding identifier.
- `classification`: `bug_hit`, `valid_suggestion`, or `noise`.
- `gold_bug_ids`: Gold identifiers matched by this finding.
- `disposition`: `open`, `accepted`, `rejected`, `disputed`, `fixed`, or `deferred`.
- `reason`: Short evidence-based classification reason.

Multi-round evaluations may also include:

- `condition`: Review configuration such as `single` or `adaptive_swarm`. Defaults to `default`.
- `round`: Positive review round number. Defaults to `1`.
- `agent_role`: Coordinator or specialist role that produced the finding.
- `predicted_priority`: Reported `P0`, `P1`, `P2`, or `P3` priority.
- `duplicate_of`: Earlier finding identifier with the same root cause.
- `root_cause_id`: Stable root-cause label used to validate deduplication.

A `bug_hit` must reference at least one gold identifier. Other classifications must not reference gold identifiers.

## Metrics

Run:

`uv run python scripts/evaluate_reviews.py --cases fixtures/cr-bench-smoke.jsonl fixtures/c-crab-smoke.jsonl --judgments fixtures/smoke-judgments.jsonl`

The evaluator reports aggregate, per-condition, and per-benchmark metrics:

- Recall: Unique gold defects hit divided by all gold defects.
- Canonical precision: Canonical `bug_hit` comments divided by canonical comments.
- Canonical usefulness: Canonical useful comments divided by canonical comments.
- Canonical noise rate: Canonical noise comments divided by canonical comments.
- Delivery noise rate: Noise and duplicate comments divided by all delivered comments.
- Signal-to-noise ratio: Canonical useful comments divided by canonical noise comments.
- First-round P1 recall: Initial-target P1 defects found in round one divided by all initial-target P1 defects.
- Macro first-round P1 recall: Mean per-case-replicate P1 recall, excluding units without P1 gold.
- Macro recall: Mean per-case-replicate gold recall.
- P1 escape rate: One minus first-round P1 recall.
- Late P1 rate: Initial-target P1 defects first found after round one divided by all initial-target P1 defects.
- Residual P1 rate at `K`: Initial-target P1 defects not found by the completed endpoint divided by all initial-target P1 defects.
- P1 saturation gap: Final P1 recall minus first-round P1 recall.
- Blocking recognition recall: Gold P1 defects found and reported as `P0` or `P1` divided by all gold P1 defects.
- Duplicate burden: Duplicate finding occurrences divided by all raw finding occurrences.
- Priority-label coverage: Eligible bug-hit comments with a priority divided by all eligible bug-hit comments.
- Tokens per unique gold hit: Measured tokens divided by unique gold defects found.
- Resource ratio: Treatment resource use divided by control resource use on completed pairs.

The noise rates are comment-level burden. They are not statistical rates over true negatives.

The signal-to-noise ratio is `null` when no noise exists. Do not replace that result with an invented value.

Use `--baseline-report <report.json>` to show metric deltas. The evaluator does not invent pass thresholds.

## Evaluation Process

1. Run the synthetic smoke fixtures.
2. Compare the legacy aggregate fields with `fixtures/smoke-expected.json`:

   ```bash
   uv run python scripts/evaluate_reviews.py \
     --cases fixtures/cr-bench-smoke.jsonl fixtures/c-crab-smoke.jsonl \
     --judgments fixtures/smoke-judgments.jsonl \
     | jq '.aggregate | {case_count, finding_count, false_positive_count, false_positive_rate, gold_bug_count, hit_gold_bug_count, precision, recall, signal_to_noise, useful_finding_count, usefulness}'
   ```

   The full evaluator report uses a newer schema and contains additional sections.
3. Normalize licensed benchmark exports to the fixture format.
4. Run the same reviewer configuration more than once when nondeterminism matters.
5. Record the model, prompt or skill revision, tools, repository state, and runtime limits.
6. Compare metrics and inspect false positives manually.
7. Keep behavioral c-CRAB pass results beside comment-quality metrics.
8. Inspect reviewer-critic traces when a condition uses structured adversarial audit.

## Adversarial Audit Trace

Store audit traces separately from finding judgments. The evaluator does not infer protocol quality from final comments alone.

Record these fields for every audited candidate:

- `case_id`, `run_id`, and stable candidate identifier.
- Source lane and candidate priority before audit.
- Critic verdict and cited evidence.
- Scope status.
- Reviewer response and evidence change.
- Final lifecycle state.
- Audit mode: `independent` or `local`.
- Exchange count and stopping reason.

Manually classify converged traces as one of:

- `evidence_grounded`: Evidence supports the final state.
- `false_consensus`: Agents agreed without enough evidence.
- `scope_expansion`: The process promoted unrelated work into a finding.
- `protocol_violation`: The artifact changed, context differed, or disagreement ended without the required response.
- `unresolved`: The audit stopped without a supported result.

Report counts and denominators for every trace class. Do not label agreement as grounded without inspecting its evidence.

## Multi-Round Comparison

Freeze the same base and head revisions across rounds. A changed target starts a new evaluation case.

Bind every run to the case repository, revisions, and diff digest. Reject mismatched findings or runs.

Compare these conditions when measuring multi-agent value:

1. One agent with one pass.
2. One agent with fresh repeated passes and a matched resource budget.
3. Fixed-theme specialist lanes.
4. Risk-adaptive specialist lanes.
5. Risk-adaptive lanes followed by an unconstrained critic.
6. Risk-adaptive lanes followed by the structured adversarial audit.
7. Hybrid theme and component lanes followed by the structured adversarial audit.

The repeated single-agent condition separates architecture effects from additional compute.

The unconstrained-critic condition separates interaction from the structured disagreement contract.

Use gold priority for severity recall. Use predicted priority only for severity calibration.

Report cumulative P1 recall and marginal new P1 findings by round. Select repetition counts after a variance pilot.

Score each replicate before aggregation. Compare only completed case-replicate pairs across conditions.

Report excluded pairs and failed runs. Use measured run resources for cost comparisons.

Do not tune only for recall. Increased recall can reduce usefulness and increase noise.

Also compare false-consensus, scope-expansion, protocol-violation, and unresolved trace counts.

Treat published benchmark results as motivation, not pass thresholds. Re-measure behavior on the target model, toolset, and repository mix.
