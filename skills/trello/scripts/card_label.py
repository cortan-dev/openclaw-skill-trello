#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, print_json, main_guard

def main():
    parser = argparse.ArgumentParser(description="Add or remove a label on a card")
    parser.add_argument("--card", required=True, help="Card name or ID")
    parser.add_argument("--board", help="Board name or ID (required if card name used)")
    parser.add_argument("--list", help="List name or ID (optional context for card name)")
    parser.add_argument("--label", required=True, help="Label name or ID")
    parser.add_argument("--remove", action="store_true", help="Remove the label instead of adding it")
    args = parser.parse_args()

    client = TrelloClient()
    card = client.resolve_card(args.card, board_ref=args.board, list_ref=args.list)
    
    # We need board_id to resolve label name
    # card object from resolve_card might have board_id if ID was used, 
    # but if card name was used, resolve_card returns board_name (if provided)
    # Actually, resolve_card(ID) returns board_id. resolve_card(name) might not if matched via list.
    # Let's check card object contents.
    
    board_id = card.get("board_id")
    if not board_id:
        # If we only have list_id, we might need to fetch the list to get board_id
        if card.get("list_id"):
             list_data = client.request("GET", f"/lists/{card['list_id']}", params={"fields": "idBoard"})
             board_id = list_data["idBoard"]
        else:
             # This shouldn't happen with current resolve_card implementation
             raise Exception("Could not determine board ID for label resolution")

    label = client.resolve_label(board_id, args.label)
    
    if args.remove:
        client.remove_label_from_card(card["id"], label["id"])
        print_json({"status": "removed", "card": card["name"], "label": label["name"] or label["color"]})
    else:
        client.add_label_to_card(card["id"], label["id"])
        print_json({"status": "added", "card": card["name"], "label": label["name"] or label["color"]})

if __name__ == "__main__":
    main_guard(main)
