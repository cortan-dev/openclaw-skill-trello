#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, fail, print_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--pos", default="bottom")
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    print_json(client.create_list(board["id"], args.name, args.pos))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(exc)
