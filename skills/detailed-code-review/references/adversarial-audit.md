# Structured Adversarial Audit

Use this audit after candidate synthesis when the review needs evidence-grounded disagreement.

The audit tests the review. It does not edit or re-review the artifact without a focused hypothesis.

## Trigger gate

Run the audit when any condition holds:

- A candidate has `P0` or `P1` impact.
- A candidate relies on inferred, incomplete, or disputed evidence.
- Two lanes disagree or their findings interact.
- A high-risk invariant could support approval or block merge.
- The integration challenge creates a new blocking candidate.

The coordinator may skip the audit for a small, low-risk change with no candidates or material coverage gaps.

Record the gate decision. Do not invoke extra agents only because more agents are available.

## Roles and frozen inputs

The coordinator owns the final finding ledger.

The candidate owner acts as the reviewer. A fresh critic audits the review when delegation is permitted.

When delegation is unavailable, use a separate local critic pass. Do not call that pass independent.

Freeze these inputs during the audit:

- Exact target revisions and snapshot digests.
- The original user ask and acceptance criteria without reinterpretation.
- The artifact and relevant repository context.
- The synthesized candidate ledger and coverage matrix.
- Commands already executed and their exact results.

Reviewer and critic exchange review text only. They must not edit the artifact during the audit.

Before reading the candidate ledger, the critic forms a short independent view of the target and important invariants. This reduces anchoring.

## Critic contract

The critic checks three dimensions:

1. Validity: Does repository evidence prove each candidate's trigger and outcome?
2. Completeness: Did the candidate review miss a concrete defect or high-risk edge?
3. Scope: Does each candidate arise from the review target or a required companion change?

For every candidate, return this record:

```text
Candidate: <stable candidate ID>
Verdict: AGREE | DISAGREE_EVIDENCE | DISAGREE_CONCERN
Evidence: <file:line, execution path, command result, contract, or missing proof>
Scope: IN_SCOPE | REQUIRED_COMPANION | OUT_OF_SCOPE | UNCLEAR_INTENT
Reason: <short explanation>
```

Use the verdicts as follows:

- `AGREE`: Concrete evidence supports the candidate. Agreement alone is insufficient evidence.
- `DISAGREE_EVIDENCE`: Code, tests, configuration, or a contract contradicts the candidate.
- `DISAGREE_CONCERN`: The candidate remains plausible, but its proof is incomplete or assumption-dependent.

List missed issues separately as new candidate IDs. Include their trigger, outcome, evidence, priority, and scope status.

Do not count votes. Do not use confidence as a decision rule.

## Reviewer response contract

The candidate owner responds to every disagreement:

- For `DISAGREE_EVIDENCE`, accept the evidence and revise or reject the candidate. Otherwise, cite stronger contradicting evidence.
- For `DISAGREE_CONCERN`, prove the execution path, downgrade it to a question, mark it unresolved, or reject it.
- For `OUT_OF_SCOPE`, remove the candidate unless the user explicitly included it.
- For `REQUIRED_COMPANION`, show why the requested change cannot work safely without that companion change.
- For `UNCLEAR_INTENT`, ask a question when the ambiguity changes correctness.

A confident rebuttal does not resolve a disagreement. New evidence must change the candidate state.

Do not split one root cause into several thin findings. Keep one finding unless triggers or outcomes require separate fixes.

## Convergence and stopping

The audit converges when every candidate has one lifecycle state:

- `confirmed`
- `rejected`
- `duplicate`
- `question`
- `unresolved`

Convergence does not prove correctness. Every confirmed candidate must still satisfy the normal finding standard.

Use at most five reviewer-critic exchanges for one frozen target. Stop earlier when no evidence or candidate state changes.

If a blocking candidate remains `unresolved`, report an incomplete review. Do not force agreement to finish.

If the critic identifies a new `P0` or `P1` candidate, reopen its owning lane. Audit that candidate after focused validation.

## Scope control

Review disagreement can amplify speculative work. Apply these controls:

- Tie every candidate to the review target, changed behavior, or a required compatibility guarantee.
- Reject hypothetical improvements that do not create a concrete failure in the review target.
- Distinguish a root-cause repair from a symptom-only repair by tracing one level deeper in the call or state chain.
- Prefer the smallest fix direction that removes the demonstrated precondition.
- Treat an extra feature, refactor, or unrelated hardening idea as a non-blocking suggestion only when the user requested suggestions.

## Audit record

Keep an internal record with:

- Gate reason and audit mode: `independent`, `local`, `not_triggered`, or `not_covered`.
- Critic verdict and scope status for every candidate.
- Reviewer response and evidence change.
- New candidates, rejected candidates, and unresolved concerns.
- Exchange count and stopping reason.

The public response needs only the audit mode and material unresolved limits. Do not publish the entire debate.
