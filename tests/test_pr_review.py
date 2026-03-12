import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / ".github" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pr_review  # noqa: E402


class ParseContextTests(unittest.TestCase):
    def test_issue_comment_review_ignores_untrusted_author(self) -> None:
        event = {
            "action": "created",
            "repository": {"owner": {"login": "cortan-dev"}, "name": "openclaw-skill-trello"},
            "issue": {"number": 5, "pull_request": {"url": "https://api.github.com/repos/x/pulls/5"}},
            "comment": {
                "body": "/review",
                "author_association": "CONTRIBUTOR",
                "user": {"login": "external-user"},
            },
        }

        with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "issue_comment"}, clear=False):
            with patch("builtins.print") as mock_print:
                result = pr_review.parse_context(event)

        self.assertIsNone(result)
        mock_print.assert_called_once()
        self.assertIn("Ignoring /review from untrusted", mock_print.call_args.args[0])

    def test_issue_comment_review_allows_trusted_author(self) -> None:
        event = {
            "action": "created",
            "repository": {"owner": {"login": "cortan-dev"}, "name": "openclaw-skill-trello"},
            "issue": {"number": 5, "pull_request": {"url": "https://api.github.com/repos/x/pulls/5"}},
            "comment": {
                "body": "/review",
                "author_association": "MEMBER",
                "user": {"login": "michael"},
            },
        }
        pr_payload = {
            "number": 5,
            "head": {"sha": "abc123", "ref": "feature"},
            "base": {"ref": "main"},
            "title": "Test PR",
            "body": "PR body",
            "html_url": "https://github.com/cortan-dev/openclaw-skill-trello/pull/5",
            "draft": False,
        }

        mock_client = MagicMock()
        mock_client.get_pull_request.return_value = pr_payload

        with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "issue_comment", "GITHUB_TOKEN": "gh-token"}, clear=False):
            with patch.object(pr_review, "GitHubClient", return_value=mock_client):
                result = pr_review.parse_context(event)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.manual_rerun)
        self.assertEqual(result.trigger, "issue_comment:/review")
        self.assertEqual(result.manual_rerun_author, "michael")
        self.assertEqual(result.head_sha, "abc123")
        mock_client.get_pull_request.assert_called_once_with(5)


class ExistingCommentTests(unittest.TestCase):
    def test_find_existing_comment_matches_sha_marker(self) -> None:
        comments = [
            {"id": 1, "body": "plain comment"},
            {"id": 2, "body": "<!-- pr-review-automation:sha=deadbeef;trigger=opened -->\nreview"},
        ]

        result = pr_review.find_existing_comment(comments, "deadbeef")

        self.assertEqual(result, comments[1])


class MainFlowTests(unittest.TestCase):
    def test_main_skips_cleanly_when_no_llm_credentials_exist(self) -> None:
        event = {
            "action": "opened",
            "repository": {"owner": {"login": "cortan-dev"}, "name": "openclaw-skill-trello"},
            "pull_request": {
                "number": 5,
                "head": {"sha": "abc123", "ref": "feature"},
                "base": {"ref": "main"},
                "title": "Test PR",
                "body": "PR body",
                "html_url": "https://github.com/cortan-dev/openclaw-skill-trello/pull/5",
                "draft": False,
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            event_path = Path(tmpdir) / "event.json"
            event_path.write_text(json.dumps(event))
            stdout = io.StringIO()
            mock_client = MagicMock()
            mock_client.list_issue_comments.return_value = []
            with patch.dict(
                os.environ,
                {
                    "GITHUB_EVENT_PATH": str(event_path),
                    "GITHUB_EVENT_NAME": "pull_request",
                    "GITHUB_TOKEN": "gh-token",
                },
                clear=True,
            ):
                with patch.object(pr_review, "GitHubClient", return_value=mock_client):
                    with patch.object(pr_review, "build_review_input", return_value="review-input"):
                        with patch("sys.stdout", stdout):
                            with self.assertRaises(pr_review.ReviewError) as ctx:
                                pr_review.main()

        self.assertIn("No LLM credentials configured.", str(ctx.exception))

    def test_main_skips_duplicate_review_for_same_sha(self) -> None:
        pr_context = pr_review.PullRequestContext(
            owner="cortan-dev",
            repo="openclaw-skill-trello",
            number=5,
            head_sha="deadbeef",
            title="Test PR",
            body="PR body",
            base_ref="main",
            head_ref="feature",
            html_url="https://github.com/cortan-dev/openclaw-skill-trello/pull/5",
            is_draft=False,
            trigger="synchronize",
            manual_rerun=False,
        )
        existing_comments = [
            {"id": 9, "body": "<!-- pr-review-automation:sha=deadbeef;trigger=opened -->\nold review"}
        ]
        mock_client = MagicMock()
        mock_client.list_issue_comments.return_value = existing_comments
        stdout = io.StringIO()

        with patch.object(pr_review, "load_event", return_value={}):
            with patch.object(pr_review, "parse_context", return_value=pr_context):
                with patch.object(pr_review, "GitHubClient", return_value=mock_client):
                    with patch.dict(
                        os.environ,
                        {"GITHUB_TOKEN": "gh-token", "OPENAI_API_KEY": "openai-key"},
                        clear=False,
                    ):
                        with patch("sys.stdout", stdout):
                            exit_code = pr_review.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Review comment already exists for deadbeef. Exiting.", stdout.getvalue())
        mock_client.list_issue_comments.assert_called_once_with(5)
        mock_client.create_issue_comment.assert_not_called()
        mock_client.update_issue_comment.assert_not_called()


if __name__ == "__main__":
    unittest.main()
