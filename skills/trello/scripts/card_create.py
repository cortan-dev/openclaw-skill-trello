#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="Create a Trello card")
    parser.add_argument("--list", required=True, help="List name or Trello list ID")
    parser.add_argument("--board", help="Required when --list is a name")
    parser.add_argument("--name", required=True)
    parser.add_argument("--description")
    args = parser.parse_args()

    client = TrelloClient()
    lst = client.resolve_list(args.list, args.board)
    print_json(client.create_card(lst["id"], args.name, args.description))


if __name__ == "__main__":
    main_guard(run)
