# What we measure, and what we cannot

The goal is to find defects that matter without making the author sort through noise.

That result depends on the model, agent, tools, repository, skill, and judge. The skill has no isolated quality score.

Here are the available measurements, ordered by how closely they approach the goal.

## 1. Does the review find real defects without noise?

The paired design in `research/benchmark-design.md` compares the same agent with and without the skill.

It measures first-round P1 recall, late discovery, canonical precision, delivery noise, duplicates, time, tokens, and cost.

This is the closest available measurement. It still depends on finite gold findings and fallible judges.

A two-case paired pilot has completed. `research/results.md` records its results and limits.

## 2. Can a reported defect be resolved and tested?

c-CRAB turns review comments into executable tests and checks whether an agent can resolve them.

That provides stronger evidence than comment matching. It only covers defects that the executable pipeline can represent.

Keep this score separate from comment-quality metrics. They answer different questions.

## 3. Does the evaluator calculate its metrics correctly?

    uv run python scripts/validate_repository.py

The repository contains two synthetic cases, three gold defects, and four judged findings.

The validator runs the evaluator and compares every expected aggregate value.

This proves the fixed example is scored correctly. It does not prove the labels or review process are good.

A second synthetic fixture checks multi-round P1 discovery and compares single-agent and adaptive-swarm conditions.

## 4. Does the skill fire for the right task?

    claude plugin eval .

One case asks for a defect review and merge decision. The skill should fire.

One case asks for implementation only. The skill should stay quiet.

Discovery decides whether the procedure reaches the user. It says nothing about the quality of a completed review.

## Publication rule

Publish raw reviewer outputs, judge outputs, configuration, parser failures, and aggregate reports together.

Publish the run manifest. It proves which case, revision, condition, replicate, and round actually ran.

Do not present smoke values as model results. Do not drop failed runs from either paired condition.
