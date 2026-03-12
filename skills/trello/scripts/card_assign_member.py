#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="Assign a member to a Trello card")
    parser.add_argument("--card", required=True, help="Card name or Trello card ID")
    parser.add_argument("--member", required=True, help="Member ID, @username, username, or exact display name")
    parser.add_argument("--board", help="Board name or Trello board ID")
    parser.add_argument("--list", dest="list_name", help="List name or Trello list ID")
    args = parser.parse_args()

    client = TrelloClient()
    card = client.resolve_card(args.card, args.board, args.list_name)
    board_id = card.get("board_id") or card["raw"].get("idBoard")
    member = client.resolve_member(args.member, board_id)
    print_json(client.assign_member_to_card(card["id"], member["id"]))


if __name__ == "__main__":
    main_guard(run)
