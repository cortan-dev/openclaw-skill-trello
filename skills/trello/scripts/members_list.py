#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, main_guard, print_json

def main():
    parser = argparse.ArgumentParser(description="List members on a Trello board.")
    parser.add_argument("--board", required=True, help="Board ID or name")
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    members = client.list_members_on_board(board["id"])
    print_json(members)

if __name__ == "__main__":
    main_guard(main)
