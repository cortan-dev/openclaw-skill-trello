#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, main_guard, print_json

def run():
    parser = argparse.ArgumentParser(description="Invite a member to a Trello board by email or username.")
    parser.add_argument("--board", required=True, help="Board ID or name")
    parser.add_argument("--member", required=True, help="Email address or Trello username (with or without @)")
    parser.add_argument("--role", choices=["admin", "normal"], default="normal", help="Role for the new member (default: normal)")
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    
    # We pass the member ref directly to add_member_to_board which handles email vs username
    member_ref = args.member.lstrip("@")
    result = client.add_member_to_board(board["id"], member_ref, args.role)
    print_json(result)

if __name__ == "__main__":
    main_guard(run)
