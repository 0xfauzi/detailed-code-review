---
name: detailed-code-review
description: Review diffs, commits, pull requests, or supplied code for concrete defects and regressions. Use when the user requests a code review, PR review, change assessment, or merge-readiness check. Do not activate for implementation-only tasks or broad security audits.
---

# Detailed Code Review

Review the change as a second engineer. Find defects that the author can fix before merge.

## Review Boundary

- Treat the requested diff, commit, pull request, or files as the review target.
- Review without editing code unless the user also asks for fixes.
- Read repository instructions before judging local conventions.
- Inspect surrounding callers, tests, schemas, and configuration when they affect changed behavior.
- For diff reviews, report problems introduced by the target change.
- For whole-code reviews, report problems inside the requested target.
- Do not report unrelated legacy defects as findings.
- State when the available artifact, base revision, or runtime context limits confidence.

If the target is unclear, use the smallest discoverable change that matches the request. Ask only when different targets would produce materially different reviews.

For Git targets, resolve and record exact revisions before inspection. Read [references/review-protocol.md](references/review-protocol.md).

## Review Workflow

1. Resolve the target.
   - Identify the target mode, base revision, target revision, and changed files.
   - Use the merge base for branch and pull request reviews.
   - Record unresolved files, generated content, and unavailable dependencies.
2. Establish intent and scope.
   - Read the change description, issue, design note, or commit message.
   - Identify the intended behavior, invariants, and compatibility promises.
3. Build a change map.
   - Summarize data flow, control flow, state transitions, and external effects.
   - Identify trust boundaries, persistent data, public interfaces, and rollout dependencies.
   - Mark high-risk paths before reading line by line.
4. Inspect the implementation.
   - Trace changed values through relevant callers and consumers.
   - Test assumptions against types, schemas, documentation, and repository patterns.
   - Check failure paths, cleanup, retries, concurrency, and partial completion.
   - Read tests as evidence. Do not treat their presence as proof.
5. Validate candidate findings.
   - Reproduce the issue with an existing test or a focused command when practical.
   - Otherwise, construct a concrete execution path from input to failure.
   - Check whether nearby code, framework behavior, or configuration prevents the issue.
   - Remove style-only comments that automated tools should handle.
   - Remove findings that depend on unsupported assumptions.
6. Run the risk critique pass when the protocol marks the change as high risk.
   - Recheck the change from a fresh failure hypothesis.
   - Validate new candidates with the same finding standard.
   - Discard duplicate or speculative candidates.
7. Report findings first.
   - Order findings by impact and urgency.
   - Give each finding a stable ID such as `F1`.
   - Attach each finding to the smallest useful target line range.
   - Explain the trigger, observed or inevitable result, and user impact.
   - Suggest the direction of a fix without requiring an unrelated redesign.
   - Finish with a coverage ledger, merge verdict, and validation gaps.

For the detailed inspection checklist, read [references/review-checks.md](references/review-checks.md).

## Finding Standard

Report a finding only when all conditions hold:

- The change causes or exposes a concrete problem.
- A realistic input, state, or sequence triggers the problem.
- The repository does not already prevent or handle the problem.
- The author can act on the comment within this change or a clearly required companion change.
- The severity matches the demonstrated impact.

Use these priorities:

- `P0`: Immediate, broad failure or critical data or security impact. Stop deployment or operation.
- `P1`: Serious defect that should block merge. It affects common paths or important guarantees.
- `P2`: Real defect with limited scope. Fix it before merge when practical.
- `P3`: Minor correctness or maintainability defect with measurable future cost. Do not use for taste.

Write each title as `[P1] Concise failure statement`. Keep the body to one compact paragraph.

Distinguish these comment types:

- Finding: Evidence supports a defect. Include a priority.
- Question: Missing context prevents a conclusion. Do not present it as a defect.
- Suggestion: The current code works, but another approach may help. Mark it non-blocking.
- Affirmation: A short note can confirm a subtle invariant or valuable test. Use sparingly.

## Evidence Rules

- Prefer repository evidence and executed checks over general advice.
- Cite the relevant function, contract, test, issue, or project rule.
- Use a counterexample for boundary and state bugs.
- Use measurements for performance claims. If measurement is unavailable, request it.
- Confirm framework and dependency behavior from installed code or primary documentation.
- Treat generated code, lockfiles, vendored files, and snapshots according to repository policy.
- Do not report missing tests alone. Explain the untested behavior and the concrete regression risk.
- Never claim that tests pass unless the command completed successfully.

## Review Summary

After the findings, include a lightweight coverage ledger. List only relevant risk areas.

Use these coverage states:

- `Finding`: The area contains an actionable defect.
- `Reviewed`: Evidence supports no actionable defect.
- `Not relevant`: The area does not apply to this change.
- `Not covered`: Missing access, context, or validation prevents review.

Then state one merge verdict:

- `Block`: At least one `P0` or `P1` finding exists.
- `Request changes`: At least one `P2` finding exists and no higher finding exists.
- `Discuss`: A material question or uncovered high-risk area prevents approval.
- `Approve with follow-up`: Only `P3` findings or non-blocking suggestions remain.
- `Approve`: No actionable findings or material coverage gaps remain.

Also state one review result:

- Findings present: Summarize the main risk and name checks you ran.
- No findings: Say that no actionable defects were found. Name the reviewed scope and checks.
- Incomplete review: Explain the missing artifact or failed validation and its effect.

Do not add a long restatement of the diff. Do not bury findings under praise or general commentary.

## Finding Dispositions

Track author responses by finding ID. Use `open`, `accepted`, `rejected`, `disputed`, `fixed`, or `deferred`.

- Record the latest evidence and a short reason for every state change.
- Keep rejected and disputed findings visible in the ledger.
- Reopen a rejected finding only when new evidence changes the conclusion.
- Do not edit the repository only to store review state.

For review evaluation, fixture normalization, and quality metrics, read [references/evaluation.md](references/evaluation.md).
