import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "trello" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import board_invite
import board_remove_member
import board_member_role
from trello_api import TrelloClient

class MemberManagementTests(unittest.TestCase):
    def test_client_add_member_email(self):
        client = TrelloClient.__new__(TrelloClient)
        client.key = "k"
        client.token = "t"
        with patch.object(client, "request") as mock_request:
            client.add_member_to_board("b123", "user@example.com", "admin")
            mock_request.assert_called_once_with(
                "PUT", "/boards/b123/members", params={"type": "admin", "email": "user@example.com"}
            )

    def test_client_add_member_username(self):
        client = TrelloClient.__new__(TrelloClient)
        client.key = "k"
        client.token = "t"
        with patch.object(client, "request") as mock_request:
            client.add_member_to_board("b123", "jdoe", "normal")
            mock_request.assert_called_once_with(
                "PUT", "/boards/b123/members/jdoe", params={"type": "normal"}
            )

    def test_client_remove_member(self):
        client = TrelloClient.__new__(TrelloClient)
        client.key = "k"
        client.token = "t"
        with patch.object(client, "request") as mock_request:
            client.remove_member_from_board("b123", "m123")
            mock_request.assert_called_once_with("DELETE", "/boards/b123/members/m123")

    def test_client_update_member_role(self):
        client = TrelloClient.__new__(TrelloClient)
        client.key = "k"
        client.token = "t"
        with patch.object(client, "request") as mock_request:
            client.update_member_role_on_board("b123", "m123", "admin")
            mock_request.assert_called_once_with(
                "PUT", "/boards/b123/members/m123", params={"type": "admin"}
            )

    def test_invite_cli(self):
        calls = {}
        class FakeClient:
            def resolve_board(self, board):
                calls["resolve_board"] = board
                return {"id": "b123"}
            def add_member_to_board(self, board_id, member, role):
                calls["add_member"] = (board_id, member, role)
                return {"id": "m123"}

        with patch("board_invite.TrelloClient", return_value=FakeClient()), \
             patch.object(sys, "argv", ["board_invite.py", "--board", "B", "--member", "@jdoe", "--role", "admin"]), \
             patch("sys.stdout", new=io.StringIO()):
            board_invite.run()
        
        self.assertEqual(calls["resolve_board"], "B")
        self.assertEqual(calls["add_member"], ("b123", "jdoe", "admin"))

    def test_remove_member_cli(self):
        calls = {}
        class FakeClient:
            def resolve_board(self, board):
                return {"id": "b123"}
            def resolve_member(self, member, board_id):
                calls["resolve_member"] = (member, board_id)
                return {"id": "m123"}
            def remove_member_from_board(self, board_id, member_id):
                calls["remove_member"] = (board_id, member_id)
                return {}

        with patch("board_remove_member.TrelloClient", return_value=FakeClient()), \
             patch.object(sys, "argv", ["board_remove_member.py", "--board", "B", "--member", "jdoe"]), \
             patch("sys.stdout", new=io.StringIO()):
            board_remove_member.run()
            
        self.assertEqual(calls["resolve_member"], ("jdoe", "b123"))
        self.assertEqual(calls["remove_member"], ("b123", "m123"))

    def test_member_role_cli(self):
        calls = {}
        class FakeClient:
            def resolve_board(self, board):
                return {"id": "b123"}
            def resolve_member(self, member, board_id):
                return {"id": "m123"}
            def update_member_role_on_board(self, board_id, member_id, role):
                calls["update_role"] = (board_id, member_id, role)
                return {}

        with patch("board_member_role.TrelloClient", return_value=FakeClient()), \
             patch.object(sys, "argv", ["board_member_role.py", "--board", "B", "--member", "jdoe", "--role", "admin"]), \
             patch("sys.stdout", new=io.StringIO()):
            board_member_role.run()
            
        self.assertEqual(calls["update_role"], ("b123", "m123", "admin"))

if __name__ == "__main__":
    unittest.main()
