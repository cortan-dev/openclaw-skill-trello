#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="Unarchive a Trello card")
    parser.add_argument("--card", required=True, help="Card name or Trello card ID")
    parser.add_argument("--board", help="Board name or Trello board ID")
    parser.add_argument("--list", dest="list_name", help="List name or Trello list ID")
    args = parser.parse_args()

    client = TrelloClient()
    # Note: list_cards_on_board and list_cards_on_list use filter="all" in trello_api.py,
    # so resolve_card should find archived cards by name if board/list is provided.
    card = client.resolve_card(args.card, args.board, args.list_name)
    print_json(client.unarchive_card(card["id"]))


if __name__ == "__main__":
    main_guard(run)
