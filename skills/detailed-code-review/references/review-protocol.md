# Review Protocol

Use this protocol to resolve scope, run a risk critique, and report review coverage.

## Exact Revision Selection

Resolve symbolic references to full commit identifiers. Record the resolved values before reviewing.

### Working tree

1. Run `git status --short`.
2. Honor an explicit request for staged, unstaged, or all local changes.
3. When unspecified, review all tracked local changes against `HEAD`.
4. List untracked files separately. Inspect their contents only when they belong to the requested change.
5. State whether the target is staged, unstaged, untracked, or mixed.

Use `git diff --cached` for staged changes. Use `git diff` for tracked unstaged changes.

Use `git diff HEAD` for all tracked local changes. This includes staged and unstaged content.

### Single commit

Resolve the target with `git rev-parse --verify <commit>^{commit}`. Resolve its parent with `git rev-parse <commit>^`.

Review `git diff <parent>..<commit>`. For a root commit, use `git diff-tree --root -p <commit>`.

### Branch or pull request

Resolve the base and head commits with `git rev-parse --verify`. Then run `git merge-base <base> <head>`.

Review `git diff <merge-base>..<head>`. Record the base, head, and merge-base commit identifiers.

Do not compare the head against the current base tip. That comparison can include unrelated base-branch changes.

### Explicit range

Honor the user's endpoints. Resolve both endpoints and state whether the range uses two-dot or three-dot semantics.

Use three-dot semantics for feature-branch changes since divergence. Use two-dot semantics for exact endpoint differences.

### Scope checks

- Confirm that the diff is non-empty.
- List changed, renamed, deleted, generated, and binary files.
- Confirm that repository instructions cover the selected files.
- Record files excluded by access, size, tooling, or user scope.
- Re-resolve revisions when a remote update changes the target.

## Intent Authority

Use this order when sources conflict:

1. User acceptance criteria and explicit task constraints.
2. Linked issue, specification, or design decision.
3. Public API and compatibility contracts.
4. Repository instructions and established local behavior.
5. Tests, comments, and commit history as supporting evidence.

Ask a question when the conflict changes whether code is correct.

## High-Risk Critique Pass

Run a separate critique pass when the change affects any high-risk area:

- Authentication, authorization, secrets, privacy, or untrusted input.
- Migrations, persistent data, destructive operations, or rollback.
- Concurrency, retries, ordering, idempotency, or distributed state.
- Public APIs, serialization, protocols, or compatibility.
- Payments, quotas, billing, or other material business rules.
- Multiple services, deployment order, feature flags, or mixed versions.
- Broad cross-cutting behavior or unclear acceptance criteria.

Start the critique pass with a fresh failure hypothesis. Focus on interactions that the first pass may have missed.

Use a separate agent only when the user and host policy permit delegation. Otherwise, perform a fresh local pass.

Apply the normal finding standard to every critique result. Do not lower the evidence threshold.

## Coverage Ledger

Keep the ledger small. Include only areas that affect the change.

| Area | State | Evidence or limit |
| --- | --- | --- |
| Correctness | Reviewed | Traced changed input through named caller and consumer. |
| Failure recovery | Finding | `F2` shows a partial write after timeout. |
| Concurrency | Not relevant | The changed path has no shared or asynchronous state. |
| Runtime validation | Not covered | The required service was unavailable. |

Do not use `Reviewed` without naming evidence. Use `Not covered` when evidence is unavailable.

## Disposition Ledger

Give every finding a stable ID. Update its state after author responses or fixes.

| ID | Priority | State | Evidence and reason |
| --- | --- | --- | --- |
| F1 | P1 | accepted | The author confirmed the failing retry sequence. |
| F2 | P2 | disputed | The reviewer and author interpret the API contract differently. |

Keep previous findings visible. Add new evidence instead of silently deleting history.
