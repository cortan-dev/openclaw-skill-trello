import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "trello" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import card_assign_member  # noqa: E402
import card_unassign_member  # noqa: E402
import members_list  # noqa: E402
from trello_api import AmbiguousMatchError, TrelloClient  # noqa: E402


class MemberResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(
            os.environ,
            {
                "TRELLO_API_KEY": "key123",
                "TRELLO_TOKEN": "tok456",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_resolve_member_by_username(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.list_members_on_board = lambda board_id: [
            {"id": "a" * 24, "username": "michael", "fullName": "Michael Scott"},
            {"id": "b" * 24, "username": "dwight", "fullName": "Dwight Schrute"},
        ]

        result = TrelloClient.resolve_member(client, "@michael", "board123")

        self.assertEqual(result["id"], "a" * 24)
        self.assertEqual(result["username"], "michael")

    def test_resolve_member_by_exact_display_name(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.list_members_on_board = lambda board_id: [
            {"id": "a" * 24, "username": "michael", "fullName": "Michael Scott"},
        ]

        result = TrelloClient.resolve_member(client, "Michael Scott", "board123")

        self.assertEqual(result["id"], "a" * 24)

    def test_resolve_member_by_id_fetches_member(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.request = lambda method, path, params=None: {"id": "a" * 24, "username": "michael", "fullName": "Michael Scott"}

        result = TrelloClient.resolve_member(client, "a" * 24, "board123")

        self.assertEqual(result["id"], "a" * 24)
        self.assertEqual(result["fullName"], "Michael Scott")

    def test_resolve_member_ambiguous_raises_clear_error(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.list_members_on_board = lambda board_id: [
            {"id": "a" * 24, "username": "michael", "fullName": "Michael"},
            {"id": "b" * 24, "username": "michael", "fullName": "Michael"},
        ]

        with self.assertRaises(AmbiguousMatchError) as exc:
            TrelloClient.resolve_member(client, "michael", "board123")

        self.assertIn("Multiple members matched 'michael'", str(exc.exception))


class MemberCliTests(unittest.TestCase):
    def test_members_list_resolves_board_and_prints_json(self) -> None:
        calls = {}

        class FakeClient:
            def resolve_board(self, board):
                calls["board"] = board
                return {"id": "board123"}

            def list_members_on_board(self, board_id):
                calls["list_members_on_board"] = board_id
                return [{"id": "member123", "username": "michael"}]

        with patch.object(members_list, "TrelloClient", return_value=FakeClient()), patch.object(
            sys, "argv", ["members_list.py", "--board", "Launch Planning"]
        ), redirect_stdout(io.StringIO()) as stdout:
            members_list.run()

        self.assertEqual(calls["board"], "Launch Planning")
        self.assertEqual(calls["list_members_on_board"], "board123")
        self.assertIn('"member123"', stdout.getvalue())

    def test_card_assign_member_resolves_card_and_member(self) -> None:
        calls = {}

        class FakeClient:
            def resolve_card(self, card, board, list_name):
                calls["resolve_card"] = (card, board, list_name)
                return {"id": "card123", "board_id": "board123", "raw": {"idBoard": "board123"}}

            def resolve_member(self, member, board_id):
                calls["resolve_member"] = (member, board_id)
                return {"id": "member123"}

            def assign_member_to_card(self, card_id, member_id):
                calls["assign_member_to_card"] = (card_id, member_id)
                return {"id": card_id, "idMember": member_id}

        with patch.object(card_assign_member, "TrelloClient", return_value=FakeClient()), patch.object(
            sys,
            "argv",
            [
                "card_assign_member.py",
                "--board",
                "Launch Planning",
                "--list",
                "Doing",
                "--card",
                "Draft homepage copy",
                "--member",
                "@michael",
            ],
        ), redirect_stdout(io.StringIO()):
            card_assign_member.run()

        self.assertEqual(calls["resolve_card"], ("Draft homepage copy", "Launch Planning", "Doing"))
        self.assertEqual(calls["resolve_member"], ("@michael", "board123"))
        self.assertEqual(calls["assign_member_to_card"], ("card123", "member123"))

    def test_card_unassign_member_resolves_card_and_member(self) -> None:
        calls = {}

        class FakeClient:
            def resolve_card(self, card, board, list_name):
                calls["resolve_card"] = (card, board, list_name)
                return {"id": "card123", "board_id": "board123", "raw": {"idBoard": "board123"}}

            def resolve_member(self, member, board_id):
                calls["resolve_member"] = (member, board_id)
                return {"id": "member123"}

            def unassign_member_from_card(self, card_id, member_id):
                calls["unassign_member_from_card"] = (card_id, member_id)
                return {"id": card_id, "idMember": member_id}

        with patch.object(card_unassign_member, "TrelloClient", return_value=FakeClient()), patch.object(
            sys,
            "argv",
            [
                "card_unassign_member.py",
                "--board",
                "Launch Planning",
                "--list",
                "Doing",
                "--card",
                "Draft homepage copy",
                "--member",
                "@michael",
            ],
        ), redirect_stdout(io.StringIO()):
            card_unassign_member.run()

        self.assertEqual(calls["resolve_card"], ("Draft homepage copy", "Launch Planning", "Doing"))
        self.assertEqual(calls["resolve_member"], ("@michael", "board123"))
        self.assertEqual(calls["unassign_member_from_card"], ("card123", "member123"))


if __name__ == "__main__":
    unittest.main()
