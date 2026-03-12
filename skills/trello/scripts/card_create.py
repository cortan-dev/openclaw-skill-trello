#!/usr/bin/env python3
from __future__ import annotations

import argparse

from trello_api import TrelloClient, main_guard, print_json


def run() -> None:
    parser = argparse.ArgumentParser(description="Create a Trello card")
    parser.add_argument("--list", required=True, help="List name or Trello list ID")
    parser.add_argument("--board", help="Required when --list is a name")
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", "--desc", dest="description")
    parser.add_argument("--due", help="Due date (ISO 8601, e.g. 2026-12-25T12:00:00Z)")
    parser.add_argument("--labels", help="Comma-separated label names or IDs")
    args = parser.parse_args()

    client = TrelloClient()
    lst = client.resolve_list(args.list, args.board)
    
    label_ids = []
    if args.labels:
        for lbl_ref in args.labels.split(","):
            label = client.resolve_label(lst["board_id"], lbl_ref.strip())
            label_ids.append(label["id"])

    print_json(client.create_card(lst["id"], args.name, args.description, due=args.due, labels=label_ids))


if __name__ == "__main__":
    main_guard(run)
