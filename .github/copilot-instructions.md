# Copilot instructions for this repo

Review Python PRs as a conservative maintainer for a small CLI-first Trello skill.
Prefer precise, actionable feedback over broad style commentary.

## Priorities

1. Correctness of Trello REST API paths, params, payloads, and HTTP methods.
2. Safe behavior for operators: clear failures, no guessing, no destructive surprises.
3. Maintainability: small functions, direct control flow, readable modules.
4. Testability: logic isolated enough for unit tests without hidden network effects.
5. Scope control: preserve the v1 product boundary.

## Review principles

- Favor correctness, safety, and clarity over cleverness or abstraction.
- Recommend the smallest change that fixes the issue.
- Call out concrete risk, impact, and suggested fix.
- Do not praise code without identifying whether it is correct, safe, and maintainable.
- Do not suggest architectural churn unless the current design is clearly harmful.

## Python-specific review criteria

### Correctness and runtime behavior

- Check edge cases, `None` handling, empty collections, and unexpected Trello API responses.
- Flag mutable default arguments.
- Flag broad `except Exception` blocks unless they immediately re-raise with context.
- Flag unreachable branches, dead code, or fallback behavior that hides defects.
- Prefer explicit return paths and explicit failure modes.
- Ensure helper functions do one clear thing and have predictable side effects.

### Error handling

- Require explicit error handling; no silent failures.
- Error messages should be actionable and include the failing resource or input when safe.
- Preserve the original exception context when wrapping errors.
- Do not accept retry loops, fallback behavior, or exception swallowing that can duplicate writes or mask API failures.

### CLI and UX safety

- Preserve existing CLI flags and output shape unless the PR intentionally changes them.
- If behavior changes, require tests and release-note-worthy explanation in the PR.
- For ambiguous board/list/card matches, fail clearly instead of guessing.
- Avoid prompts, interactivity, or hidden side effects in scripts intended for automation.

### Security and secrets

- Only `TRELLO_API_KEY` and `TRELLO_TOKEN` should be read from environment variables for Trello auth.
- Never hardcode, log, print, echo, or include secrets in exceptions.
- Flag accidental leakage through debug output, reprs, or test fixtures.

### Architecture and maintainability

- Prefer thin scripts and straightforward helpers over abstraction-heavy design.
- Do not introduce classes, frameworks, dependency injection layers, or generic clients unless they clearly reduce real complexity.
- Avoid magic constants when a named constant would clarify Trello behavior.
- Prefer standard-library solutions over new dependencies.
- Keep modules cohesive; do not mix CLI parsing, network calls, and resolver logic more than necessary.

### Python style and readability

- Prefer descriptive names over short clever names.
- Prefer early returns and simple conditionals over deep nesting.
- Prefer explicit loops/branches when comprehensions or lambdas hurt readability.
- Encourage type hints on added or changed public helpers where they improve reviewability.
- Encourage docstrings for public or non-obvious functions, especially around resolver behavior and side effects.

### Tests

- Require or suggest tests for resolver logic, request construction, CLI compatibility, and failure cases.
- Tests must not make live network calls.
- Flag hidden network side effects, reliance on environment-specific state, or brittle assertions on full exception text.
- Prefer focused unit tests over broad end-to-end fixtures.

## Repo-specific must-check items

- Trello REST API paths, query params, payload fields, and HTTP methods are correct.
- Credential safety is preserved.
- Ambiguity safeguards are preserved or improved.
- v1 scope discipline is preserved.
- Backward compatibility of existing CLI flags is preserved unless intentionally changed.

## Out of scope for v1

Flag PRs that add or normalize any of the following without an explicit request:

- deletes
- checklists
- labels
- due dates
- member assignment
- webhooks
- automation
- MCP

## Strongly flag PRs that

- broaden scope without a request
- weaken ambiguity safeguards
- introduce hidden network side effects in tests
- reduce maintainability for small gains
- replace explicit control flow with abstraction that makes review harder
- add speculative generalization or premature extensibility

## Feedback style

When leaving review feedback:

- State the issue in one sentence.
- Explain why it matters in terms of correctness, safety, compatibility, or maintainability.
- Suggest the smallest acceptable fix.
- Prefer comments like "This can mis-handle ambiguous card names; fail with a clear error instead of selecting the first match." over vague comments like "Consider improving this logic."
