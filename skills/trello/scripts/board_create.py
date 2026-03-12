#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, fail, print_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", default=None)
    args = parser.parse_args()

    client = TrelloClient()
    print_json(client.create_board(args.name, args.description))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(exc)
