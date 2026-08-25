# Multi-Agent Review

Use this protocol when a change has multiple independent risk lanes or important cross-component interactions.

The protocol also works as separate local passes when delegation is unavailable.

Use independent lanes for discovery. Use structured adversarial audit for candidate-review verification.

## First classify repeated-round findings

Record the exact base and head revisions for every review round.

For working-tree targets, also record every snapshot digest listed below for each round.

Classify each later blocking finding as one of these cases:

- It existed and was discoverable in the initial revision.
- A later fix introduced it.
- New author context made it discoverable.
- New evidence changed its priority.

Only the first case measures first-round review escape.

## Coordinator

The coordinator owns scope, routing, synthesis, and the final response.

Before delegation, build an immutable review brief with:

- Exact base, head, and merge-base revisions.
- The original user ask verbatim, plus acceptance criteria and important invariants.
- Repository instructions and allowed validation commands.
- Changed files, components, callers, and consumers.
- Data, state, trust, public contract, and deployment boundaries.
- External effects and cross-component edges.
- Known validation limits.

Freeze non-commit targets before delegation. Record:

- `git status --short` output.
- A digest of the complete tracked patch against `HEAD`.
- A digest of the staged patch.
- A digest of the index entries from `git ls-files -s`.
- The untracked-file list and a content digest for each included file.

Give every specialist the same read-only worktree or materialized snapshot when possible.

If that is unavailable, compare the complete snapshot before and after every lane.

When the snapshot changes, compute the exact delta. Rerun every owner whose surface or dependency changed.

Do not include candidate findings in the initial brief. Independent inspection reduces anchoring.

Keep the target snapshot immutable. Maintain a versioned factual addendum for confirmed dependencies, contracts, and invariants.

Share the addendum with affected lanes. Do not include candidate findings or conclusions in it.

## Coverage lanes

Start with these coverage obligations:

1. Behavior, correctness, and public contracts.
2. State, data integrity, concurrency, retries, and recovery.
3. Integration and cross-component behavior.
4. Security, privacy, and trust boundaries.
5. Compatibility, deployment, and operations.

Combine low-risk obligations when one reviewer can cover them clearly.

Add a dynamic lane when the change map exposes a distinct context. Examples include migrations, payments, protocols, or frontend state.

Use independent review for one deep high-risk invariant even when no other lane applies.

Do not split only by file. Cross-file defects often follow callers, schemas, state, or deployment order.

Give every changed and affected unchanged surface one primary owner.

Give every high-risk invariant a second independent reviewer when delegation is available.

Give cross-component edges explicit ownership. Do not assume adjacent lane owners will inspect them.

## Specialist rules

Each specialist receives the same immutable brief and one assigned lens.

Specialists may inspect the entire target and relevant repository context. Their lane limits attention, not repository access.

Specialists remain read-only. They do not publish findings directly.

Treat validation commands as potentially mutating. Run them in isolated worktrees or sandboxes when practical.

Require explicit authorization before a check mutates databases, queues, cloud resources, or external services.

Prefer ephemeral external resources. Mark unsafe unavailable checks as `Not covered`.

Otherwise, serialize commands with side effects. Recheck repository and external state after each command.

Specialists work independently before synthesis. Do not share early candidates between lanes.

Each specialist returns:

- Assigned lane and inspected surfaces.
- Callers, consumers, and cross-component edges traced.
- Invariants and failure hypotheses checked.
- Commands executed and their results.
- Candidate findings with trigger, outcome, evidence, and priority.
- Rejected candidates and the evidence that prevented them.
- Uncovered risks and missing context.

A specialist may request a new lane when it discovers an unowned context. The coordinator decides the routing.

## Internal coverage matrix

Keep an internal matrix during review. The public ledger may remain concise.

| Surface or edge | Primary owner | Secondary owner | Invariant | Evidence | State |
| --- | --- | --- | --- | --- | --- |

Use `Reviewed`, `Finding`, `Not relevant`, or `Not covered` for matrix state.

The public ledger summarizes this matrix. A generic risk-area row does not replace surface ownership.

## Candidate lifecycle

Use these internal states before publication:

- `confirmed`: Evidence satisfies the finding standard.
- `rejected`: Repository evidence prevents the claimed failure.
- `duplicate`: Another candidate has the same root cause, trigger, and outcome.
- `question`: Missing intent prevents a correctness conclusion.
- `unresolved`: Required evidence remains unavailable.

Any unresolved blocking candidate prevents completion.

For confirmed blocking candidates, record one confirmation state:

- `independent_confirmed`: A separate reviewer confirmed the failure path.
- `coordinator_reproduced`: The coordinator reproduced or traced the failure without independent cognitive confirmation.
- `unconfirmed`: Neither confirmation path completed.

Do not describe a local second pass as independent confirmation.

For every candidate entering adversarial audit, also record:

- Critic verdict: `AGREE`, `DISAGREE_EVIDENCE`, or `DISAGREE_CONCERN`.
- Scope status: `IN_SCOPE`, `REQUIRED_COMPANION`, `OUT_OF_SCOPE`, or `UNCLEAR_INTENT`.
- Reviewer response and the evidence that changed or preserved its lifecycle state.

## Synthesis

The coordinator performs synthesis after independent lane work.

1. Merge lane coverage into one change graph.
2. Deduplicate findings by root cause, trigger, and observable outcome.
3. Confirm every `P0` and `P1` through an independent reviewer or coordinator reproduction.
4. Resolve disagreements through a focused check or mark them disputed.
5. Apply the trigger gate in [adversarial-audit.md](adversarial-audit.md).
6. Run the structured audit before publication when the gate triggers.
7. Inspect interactions between lanes.
8. Update the coverage, audit, and finding ledgers.
9. Produce one set of findings and one merge verdict.

Do not resolve disagreements through majority vote.

Do not treat reviewer-critic convergence as evidence. Each surviving finding must satisfy the normal finding standard.

## Integration challenge

Run a fresh challenge after synthesis. Focus on missed blocking defects across lane boundaries.

Assign one challenge owner. Record reviewed edges, tested hypotheses, commands, rejected candidates, and uncovered areas.

Call the challenge independent only when a separate reviewer performs it.

If the challenge finds a new `P0` or `P1` candidate, reopen the affected lanes.

Rebuild the relevant change graph before continuing. Route the new candidate through structured adversarial audit.

Do not repeat an unchanged pass without a new hypothesis.

## Completion gate

The review completes only when all conditions hold:

- Every changed and affected unchanged surface has an owner.
- Every relevant coverage lane has evidence.
- Every high-risk edge and invariant has a result.
- Every high-risk invariant has a secondary reviewer when delegation is available.
- Every candidate has an internal lifecycle state.
- Every candidate that entered adversarial audit has a critic verdict, scope status, and evidence-backed resolution.
- No blocking candidate remains `unresolved` or `unconfirmed`.
- No audit-required blocking candidate remains disputed or unaudited.
- Every unavailable check appears as `Not covered`.
- The integration challenge record is complete and finds no new blocking defect.

When delegation is unavailable, record reduced independence for each high-risk invariant.

Do not give an unconditional approval when that limitation affects confidence.

Report an incomplete review when resource or access limits prevent the gate from passing.

## Failure controls

- Use risk-based routing to limit cost and duplicate work.
- Keep specialists read-only to prevent shared-state conflicts.
- Use one immutable brief so every lane reviews the same target.
- Preserve independent inspection to reduce anchoring.
- Freeze the artifact during reviewer-critic exchanges.
- Require evidence changes to resolve disagreement. Do not accept confident rebuttals alone.
- Apply scope status before a concern becomes a finding.
- Deduplicate before reporting to control comment volume.
- Treat more agents as additional evidence, not proof of completeness.

## Cross-round identity

Load the prior finding ledger before reviewing a later revision.

Fingerprint each finding by root cause, trigger, observable outcome, and affected contract.

Map moved or rewritten code to an existing finding ID when the fingerprint remains the same.
