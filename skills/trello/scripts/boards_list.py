#!/usr/bin/env python3
from trello_api import TrelloClient, fail, print_json


def main() -> None:
    client = TrelloClient()
    print_json(client.get_boards())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(exc)
