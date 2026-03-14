#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, main_guard, print_json

def run():
    parser = argparse.ArgumentParser(description="Remove a member from a Trello board.")
    parser.add_argument("--board", required=True, help="Board ID or name")
    parser.add_argument("--member", required=True, help="Member ID, username (with or without @), or full name")
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    member = client.resolve_member(args.member, board["id"])
    
    result = client.remove_member_from_board(board["id"], member["id"])
    print_json(result)

if __name__ == "__main__":
    main_guard(run)
