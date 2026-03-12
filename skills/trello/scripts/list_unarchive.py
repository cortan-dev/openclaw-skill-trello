#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="Unarchive (reopen) a Trello list")
    parser.add_argument("--list", required=True, help="List name or Trello list ID")
    parser.add_argument("--board", help="Board name or Trello board ID (required if list is a name)")
    args = parser.parse_args()

    client = TrelloClient()
    # list_lists uses filter="all" in trello_api.py, so it finds archived lists.
    lst = client.resolve_list(args.list, args.board)
    print_json(client.unarchive_list(lst["id"]))


if __name__ == "__main__":
    main_guard(run)
