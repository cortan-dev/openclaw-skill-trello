#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="Get Trello board details")
    parser.add_argument("--board", required=True, help="Board name or Trello board ID")
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    details = client.get_board(board["id"])
    details["lists"] = client.list_lists(board["id"])
    print_json(details)


if __name__ == "__main__":
    main_guard(run)
