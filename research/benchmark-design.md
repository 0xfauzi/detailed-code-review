# Benchmark Design

This design measures the full model, agent, tool, and skill configuration.

It does not claim that the skill has model-independent performance.

## Question

Does `detailed-code-review` improve review quality for the same model and agent configuration?

## Paired conditions

Run every selected case under both conditions:

- Control: The agent receives a minimal code review request without the skill.
- Treatment: The same agent receives the same request with the skill installed.

Randomize condition order for each case. Keep every other setting fixed.

## Public datasets

Use [Code Review Bench](https://github.com/withmartian/code-review-benchmark) as the primary fixed benchmark.

Use [c-CRAB](https://github.com/c-CRAB-Benchmark/dataset) for executable confirmation.

Use [SWE-PRBench](https://github.com/FoundryHQ-AI/swe-prbench) for independent context and difficulty analysis.

Record each dataset commit and license. Fetch datasets during evaluation instead of copying them here.

## Frozen configuration

Record these values before generating outputs:

- Model identifier and release.
- Agent name and version.
- Skill commit.
- Dataset commit and selected split.
- Judge model, prompt, and rubric.
- Reasoning effort and sampling settings.
- Tool access, repository access, and network access.
- Token, time, and cost limits.
- Run order and random seed.

Do not change a frozen value after viewing scores. Record any deviation beside the result.

## Pilot and repetitions

Run a small end-to-end pilot first. Confirm parsing, judging, scoring, and artifact capture.

Measure repeated-run variance on the pilot. Use that variance to select the final repetition count.

Do not invent a repetition count. Do not remove failed runs from either condition.

## Metrics

Report these measures for each condition and their paired difference:

- Gold-defect recall.
- Finding precision.
- Usefulness.
- False-positive count and rate.
- Signal-to-noise ratio.
- `F0.5`, which weights precision above recall.
- Duplicate-finding rate.
- Severity agreement.
- Wall time, token usage, and cost.
- Executable resolution rate for c-CRAB.

Keep executable resolution separate from comment-quality judgments.

## Judging

Hide the condition label from the judge. Match findings to gold defects by underlying issue.

Keep raw reviewer outputs and raw judge outputs. Publish parser and judge failures.

Use human review on a measured sample. Report agreement between human and model judgments.

## Analysis

Use paired bootstrap confidence intervals across cases. Record the resampling method and count.

Report results by language, issue type, difficulty, and risk area when the dataset supports them.

Do not hide metric regressions behind one composite score.

## Failure modes

- Training contamination can inflate performance.
- Judge preference can reward one writing style.
- More comments can increase recall while reducing usefulness.
- Extra context can reduce attention to changed lines.
- Tool failures can differ between paired conditions.
- Manual case removal can create selection bias.

Record these limits in every published result.
