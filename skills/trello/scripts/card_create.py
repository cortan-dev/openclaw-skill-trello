#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, fail, print_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", required=True)
    parser.add_argument("--list", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--desc", default=None)
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    trello_list = client.resolve_list(board["id"], args.list)
    print_json(client.create_card(trello_list["id"], args.name, args.desc))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(exc)
