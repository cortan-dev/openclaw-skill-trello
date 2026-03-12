# Copilot instructions for this repo

Review Python PRs for:

- correctness of Trello REST API paths, params, and HTTP methods
- credential safety: only `TRELLO_API_KEY` and `TRELLO_TOKEN` from env vars; never hardcode or print secrets
- safe ambiguity handling: if multiple boards/lists/cards match, fail clearly instead of guessing
- readable, thin scripts over abstraction-heavy design
- explicit error handling; no silent failures
- v1 scope discipline: do not add deletes, checklists, labels, due dates, member assignment, webhooks, automation, or MCP
- test coverage for resolver logic, request construction, and failure cases
- CLI backward compatibility: preserve existing flags unless intentionally changed

Flag PRs that:

- broaden scope without a request
- weaken ambiguity safeguards
- introduce hidden network side effects in tests
- reduce maintainability for small gains
