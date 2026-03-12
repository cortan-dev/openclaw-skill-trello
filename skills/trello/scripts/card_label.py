#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, TrelloError, print_json, main_guard

def run():
    parser = argparse.ArgumentParser(description="Add or remove a label on a card")
    parser.add_argument("--card", required=True, help="Card name or ID")
    parser.add_argument("--board", help="Board name or ID (required if card name used)")
    parser.add_argument("--list", dest="list_name", help="List name or ID (optional context for card name)")
    parser.add_argument("--label", required=True, help="Label name or ID")
    parser.add_argument("--remove", action="store_true", help="Remove the label instead of adding it")
    args = parser.parse_args()

    client = TrelloClient()
    card = client.resolve_card(args.card, args.board, args.list_name)
    
    board_id = card.get("board_id") or card["raw"].get("idBoard")
    if not board_id:
        raise TrelloError(f"Could not determine board for card '{args.card}' to resolve label '{args.label}'.")

    label = client.resolve_label(board_id, args.label)
    
    if args.remove:
        client.remove_label_from_card(card["id"], label["id"])
        print_json({"status": "removed", "card": card["name"], "label": label.get("name") or label.get("color")})
    else:
        client.add_label_to_card(card["id"], label["id"])
        print_json({"status": "added", "card": card["name"], "label": label.get("name") or label.get("color")})

if __name__ == "__main__":
    main_guard(run)