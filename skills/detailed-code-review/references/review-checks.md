# Detailed Review Checks

Use this reference to inspect non-trivial changes. Select checks that match the code and risk.

## Intent and Scope

- Does the implementation solve the stated problem?
- Does it change behavior beyond the stated scope?
- Does the diff include temporary, generated, debug, or unrelated content?
- Does the change depend on an unstated deployment order or companion change?
- Is the change small enough to reason about? If not, identify the risky boundary.
- Does a candidate finding require work outside the original ask?
- Is that work a required companion fix, or only a plausible improvement?

## Correctness and Contracts

- Trace normal, empty, minimum, maximum, malformed, and repeated inputs.
- Check off-by-one conditions, units, signs, ordering, rounding, and time zones.
- Check nullability, optional values, default values, and type conversions.
- Compare return values, exceptions, side effects, and error codes with callers.
- Check whether renamed or moved behavior leaves stale callers or registrations.
- Check compatibility for public APIs, CLI flags, file formats, and serialized data.

## State, Data, and Concurrency

- Model each state transition and rejected transition.
- Check atomicity across database, cache, queue, filesystem, and network effects.
- Check retries for idempotency and duplicated effects.
- Check transaction boundaries and partial failure behavior.
- Check race windows, lost updates, ordering, cancellation, and lock scope.
- Check migrations for old and new application versions running together.
- Check rollback behavior and irreversible writes.

## Failure and Recovery

- Follow every error branch to the caller or user-visible result.
- Check cleanup after exceptions, early returns, timeouts, and cancellation.
- Check resource lifetimes for files, sockets, processes, handles, and locks.
- Check whether fallback behavior hides corruption or changes guarantees.
- Check retry limits, backoff, dead-letter handling, and duplicate processing.
- Check whether logging preserves diagnosis without exposing sensitive data.

## Security and Privacy

Apply these checks when the change crosses a trust boundary or handles sensitive data.

- Validate authorization at the operation boundary, not only in the interface.
- Trace untrusted input into queries, templates, shells, paths, and interpreters.
- Check secret handling, logging, data retention, and response exposure.
- Check redirects, URL fetching, archive extraction, and file paths.
- Check dependency or configuration changes for weakened protections.
- Request a dedicated security review when the risk exceeds ordinary review scope.

## Performance and Operations

- Identify loops over network, storage, database, or unbounded collections.
- Check query count, payload size, allocation, caching, and repeated computation.
- Check startup, shutdown, health checks, and degraded dependencies.
- Check feature flags, observability, rollout controls, and rollback signals.
- Require a benchmark or production measurement for material performance claims.

## Tests and Documentation

- Map each changed behavior and failure mode to test evidence.
- Check that a test fails without the fix when it claims regression coverage.
- Check assertions for the intended result, not only successful execution.
- Check test isolation, deterministic time, randomness, and external state.
- Check whether mocks preserve the behavior that matters.
- Check user, operator, API, and migration documentation when contracts change.

## Second-Order Effects

- Which callers inherit the new behavior?
- Which caches, indexes, metrics, and alerts depend on the old behavior?
- Can one failed step leave later work unsafe?
- Can retries, reordering, or delayed events violate an invariant?
- Does the fix create a new failure class under load or mixed versions?
- Does a local simplification shift complexity into another component?

## Review Claim Discipline

- Can one root cause explain several proposed comments? If yes, keep one finding.
- Did an agent convert a hedge or hypothetical concern into a claimed defect?
- Did conversational agreement replace a code path, contract, test, or measurement?
- Did a confident rebuttal suppress evidence-backed dissent?
- Does the candidate repair the root cause, or only reapply state after the destructive operation?
- Does the proposed fix direction add an unrelated feature, refactor, or hardening change?
- Can the reviewer state why the smallest in-scope fix removes the demonstrated failure precondition?

## Candidate Finding Verification

Before reporting a candidate, answer these questions:

1. What exact input, state, or event sequence triggers it?
2. Which changed line creates the failure?
3. What observable result follows?
4. What repository evidence confirms the path?
5. Does existing validation, typing, configuration, or framework behavior prevent it?
6. Can the author resolve it without expanding the review into unrelated work?
7. Is its scope `IN_SCOPE`, `REQUIRED_COMPANION`, `OUT_OF_SCOPE`, or `UNCLEAR_INTENT`?
8. Did any disagreement change because of new evidence rather than confidence or repetition?

If any answer remains speculative, gather more evidence or downgrade it to a question.
