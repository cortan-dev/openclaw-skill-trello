#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="Move a Trello card to another list")
    parser.add_argument("--card", required=True, help="Card name or Trello card ID")
    parser.add_argument("--source-board", help="Board name or ID for card lookup")
    parser.add_argument("--source-list", help="List name or ID for card lookup")
    parser.add_argument("--target-list", required=True, help="Target list name or Trello list ID")
    parser.add_argument("--target-board", help="Required when --target-list is a name")
    args = parser.parse_args()

    client = TrelloClient()
    card = client.resolve_card(args.card, args.source_board, args.source_list)
    target = client.resolve_list(args.target_list, args.target_board)
    print_json(client.move_card(card["id"], target["id"]))


if __name__ == "__main__":
    main_guard(run)
