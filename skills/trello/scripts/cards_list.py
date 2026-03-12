#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, TrelloError, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="List Trello cards on a board or list")
    parser.add_argument("--board", help="Board name or Trello board ID")
    parser.add_argument("--list", dest="list_name", help="List name or Trello list ID")
    args = parser.parse_args()

    client = TrelloClient()
    if args.list_name:
        lst = client.resolve_list(args.list_name, args.board)
        print_json(client.list_cards_on_list(lst["id"]))
        return
    if args.board:
        board = client.resolve_board(args.board)
        print_json(client.list_cards_on_board(board["id"]))
        return
    raise TrelloError("Provide --board or --list.")


if __name__ == "__main__":
    main_guard(run)
