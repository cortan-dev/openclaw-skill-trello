#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, fail, print_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", required=True)
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    print_json(client.get_board(board["id"]))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(exc)
