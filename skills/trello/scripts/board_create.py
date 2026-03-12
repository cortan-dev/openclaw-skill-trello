#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="Create a Trello board")
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", "--desc", dest="description")
    args = parser.parse_args()

    client = TrelloClient()
    print_json(client.create_board(args.name, args.description))


if __name__ == "__main__":
    main_guard(run)
