#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, TrelloError, fail, print_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board")
    parser.add_argument("--list")
    args = parser.parse_args()

    if not args.board and not args.list:
        raise TrelloError("Provide --board or --list.")

    client = TrelloClient()
    if args.list:
        if not args.board:
            raise TrelloError("When using --list by human name, also provide --board.")
        board = client.resolve_board(args.board)
        trello_list = client.resolve_list(board["id"], args.list)
        print_json(client.get_cards_for_list(trello_list["id"]))
        return

    board = client.resolve_board(args.board)
    print_json(client.get_cards_for_board(board["id"]))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(exc)
