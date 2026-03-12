#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, TrelloError, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="Update a Trello card title and/or description")
    parser.add_argument("--card", required=True, help="Card name or Trello card ID")
    parser.add_argument("--board", help="Board name or Trello board ID")
    parser.add_argument("--list", dest="list_name", help="List name or Trello list ID")
    parser.add_argument("--name")
    parser.add_argument("--description", "--desc", dest="description")
    parser.add_argument("--due", help="Due date (ISO 8601, e.g. 2026-12-25T12:00:00Z or 'null' to clear)")
    parser.add_argument("--start", help="Start date (ISO 8601, e.g. 2026-12-25T12:00:00Z or 'null' to clear)")
    args = parser.parse_args()

    if args.name is None and args.description is None and args.due is None and args.start is None:
        raise TrelloError("Provide at least one property to update (--name, --description, --due, --start).")

    client = TrelloClient()
    card = client.resolve_card(args.card, args.board, args.list_name)
    print_json(client.update_card(card["id"], name=args.name, desc=args.description, due=args.due, start=args.start))


if __name__ == "__main__":
    main_guard(run)
