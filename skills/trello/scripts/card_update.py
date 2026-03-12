#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, TrelloError, fail, print_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", required=True)
    parser.add_argument("--card", required=True)
    parser.add_argument("--name")
    parser.add_argument("--desc")
    args = parser.parse_args()

    if args.name is None and args.desc is None:
        raise TrelloError("Provide --name and/or --desc.")

    client = TrelloClient()
    board = client.resolve_board(args.board)
    card = client.resolve_card(board_id=board["id"], card_ref=args.card)
    print_json(client.update_card(card["id"], name=args.name, desc=args.desc))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(exc)
