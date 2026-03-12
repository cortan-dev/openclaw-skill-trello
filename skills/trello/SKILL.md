---
name: trello
description: General-purpose Trello operations via Trello's official REST API using TRELLO_API_KEY and TRELLO_TOKEN. Use when creating or managing Trello boards, lists, and cards from prompts, including: creating boards/lists/cards, moving cards between lists, commenting on cards, attaching links, listing boards/lists/cards, getting board/card details, updating card title/description, and archiving cards. Resolve human names to Trello IDs internally and fail safely with one clarifying question when a name matches multiple Trello objects.
---

# Trello Skill

Use the bundled Python scripts for Trello v1 operations.

## Auth

Require these environment variables:

```bash
export TRELLO_API_KEY=...
export TRELLO_TOKEN=...
```

Do not embed credentials in prompts, files, or command arguments.

## Files

- Shared client: `scripts/trello_api.py`
- Actions:
  - `scripts/board_create.py`
  - `scripts/list_create.py`
  - `scripts/card_create.py`
  - `scripts/card_move.py`
  - `scripts/card_comment.py`
  - `scripts/card_attach_link.py`
  - `scripts/boards_list.py`
  - `scripts/lists_list.py`
  - `scripts/cards_list.py`
  - `scripts/board_get.py`
  - `scripts/card_get.py`
  - `scripts/card_update.py`
  - `scripts/card_archive.py`

## Operating rules

- Prefer human names in prompts; let the scripts resolve Trello IDs.
- If multiple boards, lists, or cards match a name, stop and ask one clarifying question.
- Do not hard delete cards in v1.
- Do not invent workflow logic, labels, due dates, members, checklists, or automation.
- Return JSON output from scripts directly or summarize it briefly.

## Examples

```bash
python3 skills/trello/scripts/board_create.py --name "Launch Board" --description "v1 tracking"
python3 skills/trello/scripts/list_create.py --board "Launch Board" --name "Todo"
python3 skills/trello/scripts/list_create.py --board "Launch Board" --name "Doing"
python3 skills/trello/scripts/card_create.py --board "Launch Board" --list "Todo" --name "Draft landing page" --desc "Collect final copy"
python3 skills/trello/scripts/card_move.py --board "Launch Board" --card "Draft landing page" --to-list "Doing"
python3 skills/trello/scripts/card_comment.py --board "Launch Board" --card "Draft landing page" --text "Started implementation"
python3 skills/trello/scripts/card_attach_link.py --board "Launch Board" --card "Draft landing page" --url "https://example.com/spec" --name "Spec"
python3 skills/trello/scripts/boards_list.py
python3 skills/trello/scripts/lists_list.py --board "Launch Board"
python3 skills/trello/scripts/cards_list.py --board "Launch Board"
python3 skills/trello/scripts/card_get.py --board "Launch Board" --card "Draft landing page"
python3 skills/trello/scripts/card_update.py --board "Launch Board" --card "Draft landing page" --name "Draft homepage" --desc "Copy approved"
python3 skills/trello/scripts/card_archive.py --board "Launch Board" --card "Draft homepage"
```

## Prompt patterns

Use prompts like:

- "Create a Trello board named Launch Board."
- "On Launch Board, create lists Todo and Doing."
- "Create a card named Draft landing page in Todo on Launch Board with description Collect final copy."
- "Move Draft landing page to Doing on Launch Board."
- "Comment on Draft landing page on Launch Board: Started implementation."
- "Attach https://example.com/spec to Draft landing page on Launch Board named Spec."
- "List boards."
- "List lists on Launch Board."
- "List cards on Launch Board."
- "Get details for card Draft landing page on Launch Board."
- "Update Draft landing page on Launch Board to Draft homepage and set description to Copy approved."
- "Archive Draft homepage on Launch Board."

## Smoke test

Run this sequence after setting auth:

```bash
python3 skills/trello/scripts/board_create.py --name "OpenClaw Trello Smoke"
python3 skills/trello/scripts/list_create.py --board "OpenClaw Trello Smoke" --name "Inbox"
python3 skills/trello/scripts/list_create.py --board "OpenClaw Trello Smoke" --name "Done"
python3 skills/trello/scripts/card_create.py --board "OpenClaw Trello Smoke" --list "Inbox" --name "Smoke card" --desc "Created by smoke test"
python3 skills/trello/scripts/card_move.py --board "OpenClaw Trello Smoke" --card "Smoke card" --to-list "Done"
python3 skills/trello/scripts/card_comment.py --board "OpenClaw Trello Smoke" --card "Smoke card" --text "Smoke test comment"
python3 skills/trello/scripts/card_attach_link.py --board "OpenClaw Trello Smoke" --card "Smoke card" --url "https://openclaw.ai" --name "OpenClaw"
python3 skills/trello/scripts/boards_list.py
python3 skills/trello/scripts/lists_list.py --board "OpenClaw Trello Smoke"
python3 skills/trello/scripts/cards_list.py --board "OpenClaw Trello Smoke"
python3 skills/trello/scripts/card_get.py --board "OpenClaw Trello Smoke" --card "Smoke card"
python3 skills/trello/scripts/card_update.py --board "OpenClaw Trello Smoke" --card "Smoke card" --name "Smoke card updated" --desc "Updated by smoke test"
python3 skills/trello/scripts/card_archive.py --board "OpenClaw Trello Smoke" --card "Smoke card updated"
```

Successful smoke test means every command exits cleanly and returns the expected Trello object JSON.
