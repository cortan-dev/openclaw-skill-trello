#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, print_json, main_guard

def run():
    parser = argparse.ArgumentParser(description="List labels on a board")
    parser.add_argument("--board", required=True, help="Board name or ID")
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    labels = client.list_board_labels(board["id"])
    print_json(labels)

if __name__ == "__main__":
    main_guard(run)
