#!/usr/bin/env python3
from __future__ import annotations

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    client = TrelloClient()
    print_json(client.list_boards())


if __name__ == "__main__":
    main_guard(run)
