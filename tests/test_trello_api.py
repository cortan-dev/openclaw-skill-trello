import io
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
    resolve_by_name_or_id,
)


class ResolveByNameOrIdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.items = [
            {"id": "1", "name": "Inbox"},
            {"id": "2", "name": "Doing"},
            {"id": "3", "name": "Done Later"},
        ]

    def test_resolves_exact_id(self) -> None:
        result = resolve_by_name_or_id("list", "2", self.items)
        self.assertEqual(result["name"], "Doing")

    def test_resolves_exact_name(self) -> None:
        result = resolve_by_name_or_id("list", "Inbox", self.items)
        self.assertEqual(result["id"], "1")

    def test_resolves_case_insensitive_name(self) -> None:
        result = resolve_by_name_or_id("list", "doing", self.items)
        self.assertEqual(result["id"], "2")

    def test_resolves_single_contains_match(self) -> None:
        result = resolve_by_name_or_id("list", "later", self.items)
        self.assertEqual(result["id"], "3")

    def test_raises_ambiguous_for_duplicate_names(self) -> None:
        items = [{"id": "1", "name": "Inbox"}, {"id": "2", "name": "Inbox"}]
        with self.assertRaises(AmbiguousMatchError):
            resolve_by_name_or_id("list", "Inbox", items)

    def test_raises_not_found(self) -> None:
        with self.assertRaises(NotFoundError):
            resolve_by_name_or_id("list", "Missing", self.items)


class TrelloClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {"TRELLO_API_KEY": "key123", "TRELLO_TOKEN": "tok456"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_requires_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(TrelloError):
                TrelloClient()

    def test_get_builds_expected_url_and_parses_json(self) -> None:
        client = TrelloClient()

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"ok": True}).encode("utf-8")

        with patch("urllib.request.urlopen", return_value=FakeResponse()) as mock_urlopen:
            result = client.get("/members/me/boards", {"fields": "name"})

        self.assertEqual(result, {"ok": True})
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.method, "GET")
        self.assertIn("/members/me/boards?", request.full_url)
        self.assertIn("key=key123", request.full_url)
        self.assertIn("token=tok456", request.full_url)
        self.assertIn("fields=name", request.full_url)

    def test_put_encodes_payload(self) -> None:
        client = TrelloClient()

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"{}"

        with patch("urllib.request.urlopen", return_value=FakeResponse()) as mock_urlopen:
            client.update_card("card123", name="Renamed", closed=True)

        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.method, "PUT")
        self.assertEqual(request.data, b"name=Renamed&closed=true")

    def test_resolve_card_requires_scope(self) -> None:
        client = TrelloClient()
        with self.assertRaises(TrelloError):
            client.resolve_card(card_ref="Card")


if __name__ == "__main__":
    unittest.main()
