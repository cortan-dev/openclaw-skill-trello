#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, main_guard, print_json

def run():
    parser = argparse.ArgumentParser(description="Unassign a member from a Trello card.")
    parser.add_argument("--card", required=True, help="Card ID or name")
    parser.add_argument("--member", required=True, help="Member ID, username (with or without @), or full name")
    parser.add_argument("--board", help="Board context for name resolution")
    parser.add_argument("--list", dest="list_name", help="List context for name resolution")
    args = parser.parse_args()

    client = TrelloClient()
    card = client.resolve_card(args.card, args.board, args.list_name)
    member = client.resolve_member(args.member, card["raw"]["idBoard"])
    
    client.unassign_member_from_card(card["id"], member["id"])
    print_json({"status": "unassigned", "card": card["name"], "member": member["fullName"]})

if __name__ == "__main__":
    main_guard(run)