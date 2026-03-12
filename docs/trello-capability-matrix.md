# Trello capability matrix

This repo stays thin, script-first, and standard-library based.

- Keep business logic in `skills/trello/scripts/trello_api.py`.
- Keep each CLI script small: parse args, resolve names, call one shared client method, print JSON.
- Do not add local state, background daemons, wrappers around wrappers, or a framework rewrite.

## Current feature coverage

| Area | Supported now | Notes |
| --- | --- | --- |
| Boards | create, list, inspect, close, reopen | Close/reopen are destructive-ish state changes; require explicit user intent. |
| Lists | create, list, archive, unarchive | Name lookup requires `--board` unless a Trello list ID is provided. |
| Cards | create, list, inspect, move, comment, attach link | Card name lookup should use `--list` when possible for tighter scope. |
| Card metadata | update title, description, due, start | `card_update.py` is the broad mutation entrypoint. |
| Due date helpers | set due, clear due | `card_due_set.py` and `card_due_clear.py` are the narrow commands when only due should change. |
| Labels | list board labels, create board labels, add/remove labels on cards | Label matching is by exact case-insensitive name or explicit label ID. |
| Members | list board members, assign/unassign card members | Member matching is exact username first, then exact full name. |
| Archive state | archive/unarchive cards and lists | These are state changes and should not be inferred from vague requests. |

## Planned / near-term features

These are reasonable additions if users ask, but they are not implemented yet:

| Area | Likely next step | Constraint |
| --- | --- | --- |
| Checklists | add/list/update checklist items | Keep as thin scripts that map directly to Trello REST endpoints. |
| Label ergonomics | maybe color-aware creation helpers | Avoid making label matching ambiguous during mutation flows. |
| Date ergonomics | dedicated start-date helper scripts if demand is real | Keep `card_update.py` backward compatible. |
| Card detail expansion | richer action/history retrieval | Prefer additive read-only scripts over changing existing JSON contracts. |

## Intentionally unsupported features

These are out of scope for this repo today:

| Area | Why unsupported |
| --- | --- |
| Automation / Butler-like workflows | Adds product logic and local workflow opinions. |
| Webhooks / long-running listeners | Moves the repo away from the script-first model. |
| Board admin / invites / permission management | Higher risk, surprising, and easier to misuse. |
| Delete flows for boards/lists/cards | Destructive and harder to recover from safely. |
| Local caching or sync state | Adds invalidation complexity without helping thin CLI use cases. |

## Safety expectations

Use the safest narrow command that satisfies the request.

- Do not infer destructive or admin intent from vague language.
- For archive/close/reopen/admin-ish actions, require explicit user wording.
- Prefer read-only commands when the user asks to inspect, verify, or compare.
- Preserve backward-compatible flags and output shape unless an issue explicitly changes them.
- For date fields, pass valid ISO 8601 values. Invalid strings should surface Trello's API error clearly.
- If a mutation target is ambiguous, stop and ask exactly one clarifying question instead of guessing.

## Ambiguity-handling rules

| Entity | Matching rule | If ambiguous |
| --- | --- | --- |
| Board | exact case-insensitive board name, or Trello board ID | Ask one clarifying question with the matching board options. |
| List | exact case-insensitive list name scoped by `--board`, or Trello list ID | Ask one clarifying question with board context. |
| Card | exact case-insensitive card name scoped by `--list` or `--board`, or Trello card ID | Ask one clarifying question with board/list context. |
| Member | exact username (with or without `@`) first, then exact full name, or Trello member ID | Ask one clarifying question listing the candidate members. |
| Label | exact case-insensitive label name scoped to the board, or Trello label ID | Ask one clarifying question listing the candidate labels. |

## Maintainability guidance

When adding future Trello scripts:

1. Add the Trello REST call to `trello_api.py` first.
2. Reuse existing resolver methods instead of re-implementing lookup logic in the CLI script.
3. Keep CLI scripts as thin adapters with a `run()` entrypoint and `main_guard(run)` footer.
4. Reuse existing flag names (`--board`, `--list`, `--card`, `--member`, `--label`) unless there is a strong compatibility reason not to.
5. Prefer adding a narrow script for a single mutation over making an existing broad script more surprising.
6. Add representative tests for:
   - request construction in `TrelloClient`
   - one CLI contract path for the new script
   - one failure path or error message when applicable
7. Update `skills/trello/SKILL.md` examples and action map whenever the command surface changes.

## Testing guidance

Tests should cover more than resolver basics.

- Keep fast unit tests in `tests/test_trello_api.py`.
- Cover representative scripts, not every line of every parser.
- Assert the actual REST path/params for new mutations.
- Assert failure-mode messaging when a script depends on ambiguity or missing context.
- Preserve backward compatibility by testing legacy flags when a script evolves.
