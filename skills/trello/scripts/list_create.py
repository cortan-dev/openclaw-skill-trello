#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="Create a Trello list")
    parser.add_argument("--board", required=True, help="Board name or Trello board ID")
    parser.add_argument("--name", required=True)
    parser.add_argument("--pos", default="bottom")
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    print_json(client.create_list(board["id"], args.name, args.pos))


if __name__ == "__main__":
    main_guard(run)
