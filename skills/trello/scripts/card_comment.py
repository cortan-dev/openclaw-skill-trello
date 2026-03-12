#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="Add a comment to a Trello card")
    parser.add_argument("--card", required=True, help="Card name or Trello card ID")
    parser.add_argument("--board", help="Board name or Trello board ID")
    parser.add_argument("--list", dest="list_name", help="List name or Trello list ID")
    parser.add_argument("--text", required=True)
    args = parser.parse_args()

    client = TrelloClient()
    card = client.resolve_card(args.card, args.board, args.list_name)
    print_json(client.add_comment(card["id"], args.text))


if __name__ == "__main__":
    main_guard(run)
