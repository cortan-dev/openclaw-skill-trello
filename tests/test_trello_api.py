import io
import json
import os
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "trello" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import card_move  # noqa: E402
import card_update  # noqa: E402
import card_unarchive  # noqa: E402
import list_archive  # noqa: E402
import list_unarchive  # noqa: E402
import board_close  # noqa: E402
import board_reopen  # noqa: E402
import list_create  # noqa: E402
import members_list # noqa: E402
import card_assign # noqa: E402
import card_unassign # noqa: E402
import labels_list # noqa: E402
import label_create # noqa: E402
import card_label # noqa: E402
from trello_api import (  # noqa: E402
    AmbiguousMatchError,
    NotFoundError,
    TrelloClient,
    TrelloError,
    looks_like_id,
)


class TrelloClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(
            os.environ,
            {
                "TRELLO_API_KEY": "key123",
                "TRELLO_TOKEN": "tok456",
                "TRELLO_API_SECRET": "sec789",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_requires_key_and_token(self) -> None:
        with patch.dict(os.environ, {"TRELLO_API_KEY": "key123", "TRELLO_TOKEN": "tok456"}, clear=True):
            client = TrelloClient()

        self.assertEqual(client.key, "key123")
        self.assertEqual(client.token, "tok456")

    def test_requires_key_and_token_when_missing(self) -> None:
        with patch.dict(os.environ, {"TRELLO_API_KEY": "key123"}, clear=True):
            with self.assertRaises(TrelloError):
                TrelloClient()

    def test_request_builds_expected_url_and_parses_json(self) -> None:
        client = TrelloClient()

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"ok": True}).encode("utf-8")

        with patch("urllib.request.urlopen", return_value=FakeResponse()) as mock_urlopen:
            result = client.request("GET", "/members/me/boards", params={"fields": "name"})

        self.assertEqual(result, {"ok": True})
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.method, "GET")
        self.assertIn("/members/me/boards?", request.full_url)
        self.assertIn("key=key123", request.full_url)
        self.assertIn("token=tok456", request.full_url)
        self.assertIn("fields=name", request.full_url)

    def test_put_uses_query_params(self) -> None:
        client = TrelloClient()

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"{}"

        with patch("urllib.request.urlopen", return_value=FakeResponse()) as mock_urlopen:
            client.update_card("card123", name="Renamed", desc="Updated")

        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.method, "PUT")
        self.assertIn("name=Renamed", request.full_url)
        self.assertIn("desc=Updated", request.full_url)
        self.assertIsNone(request.data)

    def test_request_wraps_http_errors(self) -> None:
        client = TrelloClient()
        http_error = urllib.error.HTTPError(
            url="https://api.trello.com/1/members/me/boards",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"invalid token"}'),
        )

        with patch("urllib.request.urlopen", side_effect=http_error):
            with self.assertRaises(TrelloError) as exc:
                client.request("GET", "/members/me/boards")

        self.assertIn("Trello API 401", str(exc.exception))
        self.assertIn("GET /members/me/boards", str(exc.exception))

    def test_request_wraps_network_errors(self) -> None:
        client = TrelloClient()

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
            with self.assertRaises(TrelloError) as exc:
                client.request("GET", "/members/me/boards")

        self.assertIn("Network error", str(exc.exception))

    def test_resolve_card_requires_scope(self) -> None:
        client = TrelloClient()
        with self.assertRaises(TrelloError):
            client.resolve_card("Card")


class CliCompatibilityTests(unittest.TestCase):
    def test_list_create_preserves_legacy_pos_flag(self) -> None:
        calls = {}

        class FakeClient:
            def resolve_board(self, board):
                calls["board"] = board
                return {"id": "board123"}

            def create_list(self, board_id, name, pos="bottom"):
                calls["create_list"] = (board_id, name, pos)
                return {"id": "list123"}

        with patch.object(list_create, "TrelloClient", return_value=FakeClient()), patch.object(
            sys, "argv", ["list_create.py", "--board", "Main", "--name", "Doing", "--pos", "top"]
        ), redirect_stdout(io.StringIO()):
            list_create.run()

        self.assertEqual(calls["board"], "Main")
        self.assertEqual(calls["create_list"], ("board123", "Doing", "top"))

    def test_card_move_preserves_legacy_same_board_flags(self) -> None:
        calls = {}

        class FakeClient:
            def resolve_card(self, card, board, list_name):
                calls["resolve_card"] = (card, board, list_name)
                return {"id": "card123"}

            def resolve_list(self, list_ref, board_ref=None):
                calls["resolve_list"] = (list_ref, board_ref)
                return {"id": "list123"}

            def move_card(self, card_id, list_id):
                calls["move_card"] = (card_id, list_id)
                return {"id": card_id, "idList": list_id}

        with patch.object(card_move, "TrelloClient", return_value=FakeClient()), patch.object(
            sys, "argv", ["card_move.py", "--card", "Ship it", "--board", "Roadmap", "--to-list", "Done"]
        ), redirect_stdout(io.StringIO()):
            card_move.run()

        self.assertEqual(calls["resolve_card"], ("Ship it", "Roadmap", None))
        self.assertEqual(calls["resolve_list"], ("Done", "Roadmap"))
        self.assertEqual(calls["move_card"], ("card123", "list123"))

    def test_card_update_preserves_legacy_desc_flag(self) -> None:
        calls = {}

        class FakeClient:
            def resolve_card(self, card, board, list_name):
                calls["resolve_card"] = (card, board, list_name)
                return {"id": "card123"}

            def update_card(self, card_id, name=None, desc=None, due=None, start=None):
                calls["update_card"] = (card_id, name, desc)
                return {"id": card_id, "name": name, "desc": desc}

        with patch.object(card_update, "TrelloClient", return_value=FakeClient()), patch.object(
            sys,
            "argv",
            ["card_update.py", "--card", "Ship it", "--board", "Roadmap", "--desc", "New desc"],
        ), redirect_stdout(io.StringIO()):
            card_update.run()

        self.assertEqual(calls["resolve_card"], ("Ship it", "Roadmap", None))
        self.assertEqual(calls["update_card"], ("card123", None, "New desc"))

    def test_card_unarchive(self) -> None:
        calls = {}

        class FakeClient:
            def resolve_card(self, card, board, list_name):
                calls["resolve_card"] = (card, board, list_name)
                return {"id": "card123"}

            def unarchive_card(self, card_id):
                calls["unarchive_card"] = card_id
                return {"id": card_id, "closed": False}

        with patch.object(card_unarchive, "TrelloClient", return_value=FakeClient()), patch.object(
            sys, "argv", ["card_unarchive.py", "--card", "Archived Card", "--board", "B"]
        ), redirect_stdout(io.StringIO()):
            card_unarchive.run()

        self.assertEqual(calls["resolve_card"], ("Archived Card", "B", None))
        self.assertEqual(calls["unarchive_card"], "card123")

    def test_list_archive_unarchive(self) -> None:
        calls = {}

        class FakeClient:
            def resolve_list(self, list_ref, board_ref):
                calls["resolve_list"] = (list_ref, board_ref)
                return {"id": "list123"}

            def archive_list(self, list_id):
                calls["archive_list"] = list_id
                return {"id": list_id, "closed": True}

            def unarchive_list(self, list_id):
                calls["unarchive_list"] = list_id
                return {"id": list_id, "closed": False}

        # Test archive
        with patch.object(list_archive, "TrelloClient", return_value=FakeClient()), patch.object(
            sys, "argv", ["list_archive.py", "--list", "L", "--board", "B"]
        ), redirect_stdout(io.StringIO()):
            list_archive.run()
        self.assertEqual(calls["archive_list"], "list123")

        # Test unarchive
        with patch.object(list_unarchive, "TrelloClient", return_value=FakeClient()), patch.object(
            sys, "argv", ["list_unarchive.py", "--list", "L", "--board", "B"]
        ), redirect_stdout(io.StringIO()):
            list_unarchive.run()
        self.assertEqual(calls["unarchive_list"], "list123")

    def test_board_close_reopen(self) -> None:
        calls = {}

        class FakeClient:
            def resolve_board(self, board):
                calls["resolve_board"] = board
                return {"id": "board123"}

            def close_board(self, board_id):
                calls["close_board"] = board_id
                return {"id": board_id, "closed": True}

            def reopen_board(self, board_id):
                calls["reopen_board"] = board_id
                return {"id": board_id, "closed": False}

        # Test close
        with patch.object(board_close, "TrelloClient", return_value=FakeClient()), patch.object(
            sys, "argv", ["board_close.py", "--board", "B"]
        ), redirect_stdout(io.StringIO()):
            board_close.run()
        self.assertEqual(calls["close_board"], "board123")

        # Test reopen
        with patch.object(board_reopen, "TrelloClient", return_value=FakeClient()), patch.object(
            sys, "argv", ["board_reopen.py", "--board", "B"]
        ), redirect_stdout(io.StringIO()):
            board_reopen.run()
        self.assertEqual(calls["reopen_board"], "board123")

    def test_labels_list(self) -> None:
        calls = {}

        class FakeClient:
            def resolve_board(self, board):
                calls["resolve_board"] = board
                return {"id": "board123"}

            def list_board_labels(self, board_id):
                calls["list_board_labels"] = board_id
                return [{"id": "label123", "name": "Urgent"}]

        with patch.object(labels_list, "TrelloClient", return_value=FakeClient()), patch.object(
            sys, "argv", ["labels_list.py", "--board", "B"]
        ), redirect_stdout(io.StringIO()):
            labels_list.main()
        self.assertEqual(calls["list_board_labels"], "board123")

    def test_label_create(self) -> None:
        calls = {}

        class FakeClient:
            def resolve_board(self, board):
                calls["resolve_board"] = board
                return {"id": "board123"}

            def create_board_label(self, board_id, name, color):
                calls["create_board_label"] = (board_id, name, color)
                return {"id": "label123", "name": name, "color": color}

        with patch.object(label_create, "TrelloClient", return_value=FakeClient()), patch.object(
            sys, "argv", ["label_create.py", "--board", "B", "--name", "Urgent", "--color", "red"]
        ), redirect_stdout(io.StringIO()):
            label_create.main()
        self.assertEqual(calls["create_board_label"], ("board123", "Urgent", "red"))

    def test_card_label_add_remove(self) -> None:
        calls = {}

        class FakeClient:
            def resolve_card(self, card, board_ref, list_ref):
                calls["resolve_card"] = (card, board_ref, list_ref)
                return {"id": "card123", "name": "Card", "board_id": "board123"}

            def resolve_label(self, board_id, label_ref):
                calls["resolve_label"] = (board_id, label_ref)
                return {"id": "label123", "name": "Urgent"}

            def add_label_to_card(self, card_id, label_id):
                calls["add_label"] = (card_id, label_id)
                return {}

            def remove_label_from_card(self, card_id, label_id):
                calls["remove_label"] = (card_id, label_id)
                return {}

        # Test add
        with patch.object(card_label, "TrelloClient", return_value=FakeClient()), patch.object(
            sys, "argv", ["card_label.py", "--card", "C", "--board", "B", "--label", "L"]
        ), redirect_stdout(io.StringIO()):
            card_label.main()
        self.assertEqual(calls["add_label"], ("card123", "label123"))

        # Test remove
        with patch.object(card_label, "TrelloClient", return_value=FakeClient()), patch.object(
            sys, "argv", ["card_label.py", "--card", "C", "--board", "B", "--label", "L", "--remove"]
        ), redirect_stdout(io.StringIO()):
            card_label.main()
        self.assertEqual(calls["remove_label"], ("card123", "label123"))


class ResolutionTests(unittest.TestCase):
    def test_looks_like_id(self) -> None:
        self.assertTrue(looks_like_id("a" * 24))
        self.assertFalse(looks_like_id("Inbox"))

    def test_resolve_board_exact_case_insensitive(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.list_boards = lambda: [
            {"id": "a" * 24, "name": "Inbox"},
            {"id": "b" * 24, "name": "Doing"},
        ]
        result = TrelloClient.resolve_board(client, "inbox")
        self.assertEqual(result["id"], "a" * 24)

    def test_resolve_board_ambiguous(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.list_boards = lambda: [
            {"id": "a" * 24, "name": "Inbox"},
            {"id": "b" * 24, "name": "Inbox"},
        ]
        with self.assertRaises(AmbiguousMatchError):
            TrelloClient.resolve_board(client, "Inbox")

    def test_resolve_list_not_found(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.resolve_board = lambda board: {"id": "a" * 24, "name": "Board"}
        client.list_lists = lambda board_id: [{"id": "c" * 24, "name": "Todo"}]
        with self.assertRaises(NotFoundError):
            TrelloClient.resolve_list(client, "Done", "Board")

    def test_resolve_list_by_id_fetches_board_context(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.request = lambda method, path, params=None: {
            "id": "c" * 24,
            "name": "Todo",
            "idBoard": "a" * 24,
            "closed": False,
            "pos": 1,
        }
        client.get_board = lambda board_id: {"id": board_id, "name": "Project Board"}

        result = TrelloClient.resolve_list(client, "c" * 24)

        self.assertEqual(result["id"], "c" * 24)
        self.assertEqual(result["board_id"], "a" * 24)
        self.assertEqual(result["board_name"], "Project Board")

    def test_resolve_card_by_id_fetches_board_and_list_context(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.get_card = lambda card_id: {
            "id": card_id,
            "name": "Ship it",
            "idBoard": "a" * 24,
            "idList": "b" * 24,
        }
        client.get_board = lambda board_id: {"id": board_id, "name": "Project Board"}
        client.request = lambda method, path, params=None: {"name": "Doing"}

        result = TrelloClient.resolve_card(client, "c" * 24)

        self.assertEqual(result["id"], "c" * 24)
        self.assertEqual(result["board_id"], "a" * 24)
        self.assertEqual(result["board_name"], "Project Board")
        self.assertEqual(result["list_id"], "b" * 24)
        self.assertEqual(result["list_name"], "Doing")

    def test_resolve_card_ambiguous_within_list_scope(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.resolve_list = lambda list_ref, board_ref=None: {"id": "b" * 24, "name": "Doing", "board_name": "Project Board"}
        client.list_cards_on_list = lambda list_id: [
            {"id": "c" * 24, "name": "Ship it", "idList": list_id},
            {"id": "d" * 24, "name": "Ship it", "idList": list_id},
        ]

        with self.assertRaises(AmbiguousMatchError) as exc:
            TrelloClient.resolve_card(client, "Ship it", list_ref="Doing")

        self.assertIn("Project Board", str(exc.exception))
        self.assertIn("Doing", str(exc.exception))

    def test_resolve_card_ambiguous_within_board_scope_includes_list_context(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.resolve_board = lambda board_ref: {"id": "a" * 24, "name": "Project Board"}
        client.list_lists = lambda board_id: [
            {"id": "b" * 24, "name": "Todo"},
            {"id": "c" * 24, "name": "Doing"},
        ]
        client.list_cards_on_board = lambda board_id: [
            {"id": "d" * 24, "name": "Ship it", "idList": "b" * 24},
            {"id": "e" * 24, "name": "Ship it", "idList": "c" * 24},
        ]

        with self.assertRaises(AmbiguousMatchError) as exc:
            TrelloClient.resolve_card(client, "Ship it", board_ref="Project Board")

        self.assertIn("Todo", str(exc.exception))
        self.assertIn("Doing", str(exc.exception))

    def test_resolve_member_by_username(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.list_members_on_board = lambda board_id: [
            {"id": "m1", "username": "alice", "fullName": "Alice Smith"},
            {"id": "m2", "username": "bob", "fullName": "Bob Jones"},
        ]
        
        result = TrelloClient.resolve_member(client, "alice", "b1")
        self.assertEqual(result["id"], "m1")
        
        result = TrelloClient.resolve_member(client, "@bob", "b1")
        self.assertEqual(result["id"], "m2")

    def test_resolve_member_by_fullname(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.list_members_on_board = lambda board_id: [
            {"id": "m1", "username": "alice", "fullName": "Alice Smith"},
        ]
        
        result = TrelloClient.resolve_member(client, "Alice Smith", "b1")
        self.assertEqual(result["id"], "m1")

    def test_resolve_label_by_name(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.list_board_labels = lambda board_id: [
            {"id": "l1", "name": "Urgent", "color": "red"},
            {"id": "l2", "name": "Design", "color": "blue"},
        ]
        result = TrelloClient.resolve_label(client, "b1", "urgent")
        self.assertEqual(result["id"], "l1")

    def test_resolve_label_by_color(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.list_board_labels = lambda board_id: [
            {"id": "l1", "name": "Urgent", "color": "red"},
            {"id": "l2", "name": "", "color": "blue"},
        ]
        result = TrelloClient.resolve_label(client, "b1", "blue")
        self.assertEqual(result["id"], "l2")

    def test_resolve_label_ambiguous(self) -> None:
        client = TrelloClient.__new__(TrelloClient)
        client.list_board_labels = lambda board_id: [
            {"id": "l1", "name": "Urgent", "color": "red"},
            {"id": "l2", "name": "Urgent", "color": "orange"},
        ]
        with self.assertRaises(AmbiguousMatchError):
            TrelloClient.resolve_label(client, "b1", "Urgent")


if __name__ == "__main__":
    unittest.main()
