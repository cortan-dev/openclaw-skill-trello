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
    args = parser.parse_args()

    if args.name is None and args.description is None:
        raise TrelloError("Provide --name and/or --description (or legacy --desc).")

    client = TrelloClient()
    card = client.resolve_card(args.card, args.board, args.list_name)
    print_json(client.update_card(card["id"], args.name, args.description))


if __name__ == "__main__":
    main_guard(run)
