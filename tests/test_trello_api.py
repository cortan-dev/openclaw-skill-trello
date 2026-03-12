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
import list_create  # noqa: E402
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

            def update_card(self, card_id, name=None, desc=None):
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


if __name__ == "__main__":
    unittest.main()
