#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, main_guard, print_json

def run():
    parser = argparse.ArgumentParser(description="Update a member's role on a Trello board.")
    parser.add_argument("--board", required=True, help="Board ID or name")
    parser.add_argument("--member", required=True, help="Member ID, username (with or without @), or full name")
    parser.add_argument("--role", choices=["admin", "normal"], required=True, help="New role for the member")
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    member = client.resolve_member(args.member, board["id"])
    
    result = client.update_member_role_on_board(board["id"], member["id"], args.role)
    print_json(result)

if __name__ == "__main__":
    main_guard(run)
