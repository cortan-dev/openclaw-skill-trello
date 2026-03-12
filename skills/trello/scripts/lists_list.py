#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="List Trello lists on a board")
    parser.add_argument("--board", required=True, help="Board name or Trello board ID")
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    print_json(client.list_lists(board["id"]))


if __name__ == "__main__":
    main_guard(run)
