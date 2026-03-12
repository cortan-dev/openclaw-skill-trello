#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, main_guard, print_json

def main():
    parser = argparse.ArgumentParser(description="Unassign a member from a Trello card.")
    parser.add_argument("--card", required=True, help="Card ID or name")
    parser.add_argument("--member", required=True, help="Member ID, username (with or without @), or full name")
    parser.add_argument("--board", help="Board context for name resolution")
    parser.add_argument("--list", help="List context for name resolution")
    args = parser.parse_args()

    client = TrelloClient()
    card = client.resolve_card(args.card, board_ref=args.board, list_ref=args.list)
    member = client.resolve_member(args.member, card["raw"]["idBoard"])
    
    client.unassign_member_from_card(card["id"], member["id"])
    print(f"Member '{member['fullName']}' (@{member['username']}) unassigned from card '{card['name']}'.")

if __name__ == "__main__":
    main_guard(main)
