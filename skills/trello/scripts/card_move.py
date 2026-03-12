#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, fail, print_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", required=True)
    parser.add_argument("--card", required=True)
    parser.add_argument("--to-list", required=True)
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    card = client.resolve_card(board_id=board["id"], card_ref=args.card)
    target_list = client.resolve_list(board["id"], args.to_list)
    print_json(client.update_card(card["id"], id_list=target_list["id"]))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(exc)
