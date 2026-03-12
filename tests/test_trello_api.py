import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "trello" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

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

    def test_requires_all_expected_env_vars(self) -> None:
        with patch.dict(os.environ, {"TRELLO_API_KEY": "key123", "TRELLO_TOKEN": "tok456"}, clear=True):
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

    def test_resolve_card_requires_scope(self) -> None:
        client = TrelloClient()
        with self.assertRaises(TrelloError):
            client.resolve_card("Card")


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


if __name__ == "__main__":
    unittest.main()
