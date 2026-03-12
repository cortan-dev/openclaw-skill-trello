#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="Reopen a Trello board")
    parser.add_argument("--board", required=True, help="Board name or Trello board ID")
    args = parser.parse_args()

    client = TrelloClient()
    # list_boards returns all boards by default via /members/me/boards
    board = client.resolve_board(args.board)
    print_json(client.reopen_board(board["id"]))


if __name__ == "__main__":
    main_guard(run)
