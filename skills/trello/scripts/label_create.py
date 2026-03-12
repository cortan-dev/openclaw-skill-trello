#!/usr/bin/env python3
import argparse
from trello_api import TrelloClient, print_json, main_guard

def run():
    parser = argparse.ArgumentParser(description="Create a label on a board")
    parser.add_argument("--board", required=True, help="Board name or ID")
    parser.add_argument("--name", required=True, help="Label name")
    parser.add_argument("--color", help="Label color (yellow, purple, blue, red, green, orange, black, sky, pink, lime, null)")
    args = parser.parse_args()

    client = TrelloClient()
    board = client.resolve_board(args.board)
    label = client.create_board_label(board["id"], args.name, args.color)
    print_json(label)


main = run


if __name__ == "__main__":
    main_guard(run)
