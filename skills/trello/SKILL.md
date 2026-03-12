---
name: trello
description: Manage Trello boards, lists, and cards via the Trello REST API. Use when the user wants to create boards/lists/cards, move cards, comment on cards, attach links, list boards/lists/cards, inspect board or card details, update card title/description, or archive cards. This skill is for general Trello operations, not board-specific workflow automation.
---

# Trello

Use the thin Python scripts in `scripts/` for all Trello work. They talk directly to Trello's official REST API and authenticate with these existing env vars:

- `TRELLO_API_KEY`
- `TRELLO_TOKEN`

Do not add workflow opinions. Do not invent local state. Resolve names to Trello IDs through the shared client.

## Quick start

Run scripts from the skill directory or from anywhere with the scripts directory on `PYTHONPATH`.

```bash
cd skills/trello
python3 scripts/boards_list.py
```

All scripts print JSON on success and exit non-zero on failure.

## Safety and resolution rules

- Prefer Trello IDs when the user provides them.
- When the user gives human-friendly names, let `scripts/trello_api.py` resolve them.
- If a board/list/card name matches multiple records, stop and ask exactly one clarifying question.
- For list name lookup, provide `--board` unless the user already gave a Trello list ID.
- For card name lookup, provide `--list` when possible; otherwise provide `--board`.
- v1 supports create, read/list, move, comment, attach-link, update title/description/dates, archive, member assignment, and labels.
- v1 does not support delete, checklists, webhooks, or automation.

## Commands

### Boards

Create a board:

```bash
python3 scripts/board_create.py --name "Launch Planning" --description "Q2 launch board"
```

List boards:

```bash
python3 scripts/boards_list.py
```

Get board details:

```bash
python3 scripts/board_get.py --board "Launch Planning"
```

List board labels:

```bash
python3 scripts/labels_list.py --board "Launch Planning"
```

Create a board label:

```bash
python3 scripts/label_create.py --board "Launch Planning" --name "Urgent" --color "red"
```

### Lists

Create a list on a board:

```bash
python3 scripts/list_create.py --board "Launch Planning" --name "Todo"
```

List lists on a board:

```bash
python3 scripts/lists_list.py --board "Launch Planning"
```

### Cards

Create a card:

```bash
python3 scripts/card_create.py --board "Launch Planning" --list "Todo" --name "Draft homepage copy" --description "Need first pass" --due "2026-12-25T12:00:00Z" --labels "Urgent,Design"
```

List cards on a board:

```bash
python3 scripts/cards_list.py --board "Launch Planning"
```

List cards on a list:

```bash
python3 scripts/cards_list.py --board "Launch Planning" --list "Todo"
```

Get card details:

```bash
python3 scripts/card_get.py --board "Launch Planning" --list "Todo" --card "Draft homepage copy"
```

Move a card:

```bash
python3 scripts/card_move.py --source-board "Launch Planning" --source-list "Todo" --card "Draft homepage copy" --target-board "Launch Planning" --target-list "Doing"
```

Add a comment:

```bash
python3 scripts/card_comment.py --board "Launch Planning" --list "Doing" --card "Draft homepage copy" --text "First draft is in review."
```

Attach a link:

```bash
python3 scripts/card_attach_link.py --board "Launch Planning" --list "Doing" --card "Draft homepage copy" --url "https://example.com/spec" --name "Spec"
```

Update a card (title, description, due date, start date):

```bash
python3 scripts/card_update.py --board "Launch Planning" --list "Doing" --card "Draft homepage copy" --name "Draft landing page copy" --description "First pass complete" --due "2026-12-30T17:00:00Z"
```

Clear card dates:

```bash
python3 scripts/card_update.py --board "Launch Planning" --card "Draft landing page copy" --due "null" --start "null"
```

Add a label to a card:

```bash
python3 scripts/card_label.py --board "Launch Planning" --card "Draft landing page copy" --label "Urgent"
```

Remove a label from a card:

```bash
python3 scripts/card_label.py --board "Launch Planning" --card "Draft landing page copy" --label "Urgent" --remove
```

Archive a card:

```bash
python3 scripts/card_archive.py --board "Launch Planning" --list "Doing" --card "Draft landing page copy"
```

### Members

List members on a board:

```bash
python3 scripts/members_list.py --board "Launch Planning"
```

Assign a member to a card:

```bash
python3 scripts/card_assign.py --board "Launch Planning" --list "Doing" --card "Draft landing page copy" --member "@michael"
```

Unassign a member from a card:

```bash
python3 scripts/card_unassign.py --board "Launch Planning" --list "Doing" --card "Draft landing page copy" --member "@michael"
```

## Action script map

- `scripts/trello_api.py` — shared Trello API client, auth, error handling, name resolution
- `scripts/board_create.py` — create board
- `scripts/list_create.py` — create list
- `scripts/card_create.py` — create card
- `scripts/card_move.py` — move card to another list
- `scripts/card_comment.py` — add comment to card
- `scripts/card_attach_link.py` — attach URL to card
- `scripts/boards_list.py` — list boards
- `scripts/lists_list.py` — list lists on a board
- `scripts/cards_list.py` — list cards on a board or list
- `scripts/board_get.py` — get board details
- `scripts/card_get.py` — get card details, recent comments, attachments
- `scripts/card_update.py` — update card title and/or description
- `scripts/card_archive.py` — archive card
- `scripts/members_list.py` — list members on a board
- `scripts/card_assign.py` — assign member to card
- `scripts/card_unassign.py` — unassign member from card

## Example prompts

- Create a Trello board named `Launch Planning`.
- Add a `Todo` list to the `Launch Planning` board.
- Create a card called `Draft homepage copy` in `Todo` on `Launch Planning`.
- Move `Draft homepage copy` from `Todo` to `Doing`.
- Add a comment to `Draft homepage copy`: `First draft is in review.`
- Attach `https://example.com/spec` to `Draft homepage copy` and name it `Spec`.
- List boards in Trello.
- List lists on `Launch Planning`.
- List cards on the `Todo` list in `Launch Planning`.
- Show details for the `Launch Planning` board.
- Show details for the `Draft homepage copy` card.
- Rename `Draft homepage copy` to `Draft landing page copy` and update the description to `First pass complete`.
- Archive `Draft landing page copy`.
- List members on the `Launch Planning` board.
- Assign `@michael` to `Draft landing page copy` in `Doing` on `Launch Planning`.
- Unassign `@michael` from `Draft landing page copy`.

## Smoke test

Run this sequence against a test workspace:

1. `board_create.py` to create a temporary board.
2. `list_create.py` twice to create `Todo` and `Doing`.
3. `card_create.py` to create a test card in `Todo`.
4. `card_move.py` to move it to `Doing`.
5. `card_comment.py` to add a comment.
6. `card_attach_link.py` to attach a URL.
7. `board_get.py`, `lists_list.py`, `cards_list.py`, and `card_get.py` to verify retrieval.
8. `card_update.py` to change title/description.
9. `card_archive.py` to archive the card.

If any name-based lookup is ambiguous, stop and ask one clarifying question instead of guessing.
