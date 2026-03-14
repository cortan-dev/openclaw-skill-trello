#!/usr/bin/env python3
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MAX_PATCH_CHARS = 12000
MAX_FILE_CONTENT_CHARS = 16000
MAX_FILES = 25
COMMENT_MARKER_PREFIX = "<!-- pr-review-automation"
DEFAULT_ANTHROPIC_API_BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_ANTHROPIC_ASSISTANT_MODEL = "claude-sonnet-4-5"
DEFAULT_ANTHROPIC_SPARTAN_MODEL = "claude-sonnet-4-5"
DEFAULT_GEMINI_ASSISTANT_MODEL = "gemini-2.0-flash"
DEFAULT_GEMINI_SPARTAN_MODEL = "gemini-2.0-flash"
TRUSTED_AUTHOR_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}


class ReviewError(Exception):
    pass


@dataclass
class PullRequestContext:
    owner: str
    repo: str
    number: int
    head_sha: str
    title: str
    body: str
    base_ref: str
    head_ref: str
    html_url: str
    is_draft: bool
    trigger: str
    manual_rerun: bool
    manual_rerun_author: Optional[str] = None


class GitHubClient:
    def __init__(self, token: str, owner: str, repo: str) -> None:
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base = f"https://api.github.com/repos/{owner}/{repo}"

    def _request(self, method: str, url: str, data: Optional[Dict[str, Any]] = None, accept: str = "application/vnd.github+json") -> Any:
        body = None
        headers = {
            "Accept": accept,
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "openclaw-pr-review-automation",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return None
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ReviewError(f"GitHub API {exc.code} for {url}: {detail}") from exc

    def get_pull_request(self, number: int) -> Dict[str, Any]:
        return self._request("GET", f"{self.base}/pulls/{number}")

    def list_pull_files(self, number: int) -> List[Dict[str, Any]]:
        page = 1
        files: List[Dict[str, Any]] = []
        while True:
            url = f"{self.base}/pulls/{number}/files?per_page=100&page={page}"
            batch = self._request("GET", url)
            if not batch:
                return files
            files.extend(batch)
            if len(batch) < 100:
                return files
            page += 1

    def list_issue_comments(self, number: int) -> List[Dict[str, Any]]:
        page = 1
        comments: List[Dict[str, Any]] = []
        while True:
            url = f"{self.base}/issues/{number}/comments?per_page=100&page={page}"
            batch = self._request("GET", url)
            if not batch:
                return comments
            comments.extend(batch)
            if len(batch) < 100:
                return comments
            page += 1

    def create_issue_comment(self, number: int, body: str) -> None:
        self._request("POST", f"{self.base}/issues/{number}/comments", {"body": body})

    def update_issue_comment(self, comment_id: int, body: str) -> None:
        self._request("PATCH", f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/comments/{comment_id}", {"body": body})

    def get_file_content(self, path: str, ref: str) -> Optional[str]:
        encoded_path = urllib.parse.quote(path, safe="/")
        url = f"{self.base}/contents/{encoded_path}?ref={urllib.parse.quote(ref, safe='')}"
        try:
            payload = self._request("GET", url)
        except ReviewError as exc:
            if "GitHub API 404" in str(exc):
                return None
            raise
        if not payload or payload.get("encoding") != "base64" or "content" not in payload:
            return None
        decoded = base64.b64decode(payload["content"])
        return decoded.decode("utf-8", errors="replace")

    def get_combined_status(self, ref: str) -> Dict[str, Any]:
        return self._request("GET", f"{self.base}/commits/{ref}/status")

    def get_check_runs(self, ref: str) -> Dict[str, Any]:
        return self._request("GET", f"{self.base}/commits/{ref}/check-runs", accept="application/vnd.github+json")


class LLMClient:
    def review(self, model: str, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, base_url: str = DEFAULT_GEMINI_API_BASE_URL) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def review(self, model: str, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000},
        }
        body = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "openclaw-pr-review-automation"},
        )
        try:
            with urllib.request.urlopen(req) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ReviewError(f"Gemini API {exc.code}: {detail}") from exc
        try:
            return raw["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ReviewError(f"Unexpected Gemini response shape: {json.dumps(raw)[:2000]}") from exc


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def review(self, model: str, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": model,
            "max_tokens": 2000,
            "temperature": 0.1,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/messages",
            data=body,
            method="POST",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
                "User-Agent": "openclaw-pr-review-automation",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ReviewError(f"Anthropic API {exc.code}: {detail}") from exc
        try:
            parts = raw["content"]
            text_parts = [part.get("text", "") for part in parts if part.get("type") == "text"]
            content = "\n".join(part for part in text_parts if part).strip()
            if not content:
                raise ReviewError(f"Anthropic response had no text content: {json.dumps(raw)[:2000]}")
            return content
        except (KeyError, IndexError, TypeError) as exc:
            raise ReviewError(f"Unexpected Anthropic response shape: {json.dumps(raw)[:2000]}") from exc


def load_event() -> Dict[str, Any]:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise ReviewError("GITHUB_EVENT_PATH is not set")
    return json.loads(Path(event_path).read_text())


def parse_context(event: Dict[str, Any]) -> Optional[PullRequestContext]:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    action = event.get("action", "")
    repository = event.get("repository") or {}
    owner = (repository.get("owner") or {}).get("login")
    repo = repository.get("name")
    if not owner or not repo:
        raise ReviewError("Missing repository owner/name in event payload")

    manual_rerun = False
    trigger = action or event_name

    if event_name == "pull_request":
        pr = event.get("pull_request") or {}
    elif event_name == "issue_comment":
        issue = event.get("issue") or {}
        if not issue.get("pull_request"):
            return None
        comment = event.get("comment") or {}
        if comment.get("body", "").strip() != "/review":
            return None
        author_association = (comment.get("author_association") or "").upper()
        if author_association not in TRUSTED_AUTHOR_ASSOCIATIONS:
            print(
                f"Ignoring /review from untrusted author_association={author_association or '<missing>'}"
            )
            return None
        gh = GitHubClient(os.environ["GITHUB_TOKEN"], owner, repo)
        pr = gh.get_pull_request(int(issue["number"]))
        manual_rerun = True
        trigger = "issue_comment:/review"
    elif event_name == "workflow_dispatch":
        number_raw = os.environ.get("PR_NUMBER") or ((event.get("inputs") or {}).get("pr_number"))
        if not number_raw:
            raise ReviewError("workflow_dispatch requires PR_NUMBER or inputs.pr_number")
        gh = GitHubClient(os.environ["GITHUB_TOKEN"], owner, repo)
        pr = gh.get_pull_request(int(number_raw))
        manual_rerun = True
        trigger = "workflow_dispatch"
    else:
        return None

    if not pr:
        return None

    return PullRequestContext(
        owner=owner,
        repo=repo,
        number=int(pr["number"]),
        head_sha=pr["head"]["sha"],
        title=pr.get("title", ""),
        body=pr.get("body") or "",
        base_ref=pr["base"]["ref"],
        head_ref=pr["head"]["ref"],
        html_url=pr.get("html_url", ""),
        is_draft=bool(pr.get("draft")),
        trigger=trigger,
        manual_rerun=manual_rerun,
        manual_rerun_author=((event.get("comment") or {}).get("user") or {}).get("login"),
    )


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... [truncated]"


def build_review_input(gh: GitHubClient, pr: PullRequestContext) -> str:
    review_instructions = gh.get_file_content(".github/review-instructions.md", pr.head_sha)
    files = gh.list_pull_files(pr.number)
    status = gh.get_combined_status(pr.head_sha)
    check_runs = gh.get_check_runs(pr.head_sha)

    selected_files = files[:MAX_FILES]
    rendered_files: List[str] = []
    for file in selected_files:
        filename = file.get("filename", "<unknown>")
        status_name = file.get("status", "unknown")
        additions = file.get("additions", 0)
        deletions = file.get("deletions", 0)
        patch = truncate(file.get("patch") or "", MAX_PATCH_CHARS)
        content_block = ""
        if status_name != "removed":
            content = gh.get_file_content(filename, pr.head_sha)
            if content is not None:
                content_block = truncate(content, MAX_FILE_CONTENT_CHARS)
        rendered_files.append(
            "\n".join(
                [
                    f"FILE: {filename}",
                    f"STATUS: {status_name} (+{additions} / -{deletions})",
                    "PATCH:",
                    patch or "<no patch provided>",
                    "CURRENT CONTENT:",
                    content_block or "<content unavailable>",
                ]
            )
        )

    if len(files) > MAX_FILES:
        rendered_files.append(f"Only the first {MAX_FILES} changed files are included here; the PR changes {len(files)} files total.")

    statuses = [
        {
            "context": item.get("context"),
            "state": item.get("state"),
            "description": item.get("description"),
        }
        for item in status.get("statuses", [])
    ]
    checks = [
        {
            "name": item.get("name"),
            "status": item.get("status"),
            "conclusion": item.get("conclusion"),
        }
        for item in check_runs.get("check_runs", [])
    ]

    return "\n\n".join(
        [
            "REVIEW RUBRIC (.github/review-instructions.md):\n" + (review_instructions or "<not present>"),
            "PULL REQUEST METADATA:\n" + json.dumps(
                {
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body,
                    "base_ref": pr.base_ref,
                    "head_ref": pr.head_ref,
                    "head_sha": pr.head_sha,
                    "url": pr.html_url,
                    "draft": pr.is_draft,
                    "trigger": pr.trigger,
                },
                indent=2,
            ),
            "CHECK STATUS:\n" + json.dumps({"state": status.get("state"), "statuses": statuses, "check_runs": checks}, indent=2),
            "CHANGED FILES:\n\n" + "\n\n---\n\n".join(rendered_files),
        ]
    )


def build_system_prompt(pass_name: str, persona: str) -> str:
    return (
        f"You are generating the {pass_name} for an automated pull request review. "
        f"Adopt this reviewer persona: {persona}. "
        "Read the provided review rubric first and follow it over generic habits. "
        "Be conservative, repo-specific, and actionable. "
        "Do not invent issues not supported by the diff, file contents, or checks. "
        "If nothing is blocking, say so explicitly. "
        "Use exactly these sections and headings in Markdown: "
        "### Summary, ### Blocking issues, ### Non-blocking improvements, ### Test assessment, ### Merge recommendation. "
        "Under blocking and non-blocking sections, use bullets. "
        "For each blocking issue, include the issue, why it matters, and the smallest acceptable fix. "
        "Merge recommendation must be one of: ready, ready with fixes, not ready."
    )


def build_comment_body(pr: PullRequestContext, assistant_review: str, assistant_model: str, spartan_review: str, spartan_model: str) -> str:
    marker = f"{COMMENT_MARKER_PREFIX}:sha={pr.head_sha};trigger={pr.trigger} -->"
    return "\n".join(
        [
            marker,
            f"# Automated PR review for `{pr.head_sha[:12]}`",
            "Advisory only. This does not block merges.",
            "",
            f"## Assistant pass ({assistant_model})",
            assistant_review.strip(),
            "",
            f"## Spartan engineering pass ({spartan_model})",
            spartan_review.strip(),
        ]
    )


def find_existing_comment(comments: List[Dict[str, Any]], head_sha: str) -> Optional[Dict[str, Any]]:
    needle = f"{COMMENT_MARKER_PREFIX}:sha={head_sha};"
    for comment in comments:
        body = comment.get("body") or ""
        if needle in body:
            return comment
    return None


def get_env_or_default(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def build_llm_client() -> Tuple[LLMClient, str, LLMClient, str]:
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    if not anthropic_api_key and not gemini_api_key:
        raise ReviewError(
            "No LLM credentials configured. Set ANTHROPIC_API_KEY for the assistant pass or GEMINI_API_KEY for the Spartan pass."
        )

    if anthropic_api_key and gemini_api_key:
        assistant_model = get_env_or_default("ASSISTANT_REVIEW_MODEL", DEFAULT_ANTHROPIC_ASSISTANT_MODEL)
        spartan_model = get_env_or_default("SPARTAN_REVIEW_MODEL", DEFAULT_GEMINI_SPARTAN_MODEL)
        return (
            AnthropicClient(anthropic_api_key, get_env_or_default("ANTHROPIC_BASE_URL", DEFAULT_ANTHROPIC_API_BASE_URL)),
            assistant_model,
            GeminiClient(gemini_api_key, get_env_or_default("GEMINI_BASE_URL", DEFAULT_GEMINI_API_BASE_URL)),
            spartan_model,
        )

    if anthropic_api_key:
        assistant_model = get_env_or_default("ASSISTANT_REVIEW_MODEL", DEFAULT_ANTHROPIC_ASSISTANT_MODEL)
        spartan_model = get_env_or_default("SPARTAN_REVIEW_MODEL", DEFAULT_ANTHROPIC_SPARTAN_MODEL)
        client = AnthropicClient(anthropic_api_key, get_env_or_default("ANTHROPIC_BASE_URL", DEFAULT_ANTHROPIC_API_BASE_URL))
        return client, assistant_model, client, spartan_model

    gemini_model = get_env_or_default("SPARTAN_REVIEW_MODEL", DEFAULT_GEMINI_SPARTAN_MODEL)
    assistant_model = get_env_or_default("ASSISTANT_REVIEW_MODEL", DEFAULT_GEMINI_ASSISTANT_MODEL)
    client = GeminiClient(gemini_api_key, get_env_or_default("GEMINI_BASE_URL", DEFAULT_GEMINI_API_BASE_URL))
    return client, assistant_model, client, gemini_model


def main() -> int:
    event = load_event()
    pr = parse_context(event)
    if pr is None:
        print("No matching PR context for this event. Exiting.")
        return 0
    if pr.is_draft and not pr.manual_rerun:
        print("PR is draft. Exiting until ready for review or manual rerun.")
        return 0

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        raise ReviewError("GITHUB_TOKEN is required")

    gh = GitHubClient(github_token, pr.owner, pr.repo)
    comments = gh.list_issue_comments(pr.number)
    existing_comment = find_existing_comment(comments, pr.head_sha)
    if existing_comment and not pr.manual_rerun:
        print(f"Review comment already exists for {pr.head_sha}. Exiting.")
        return 0

    review_input = build_review_input(gh, pr)
    assistant_client, assistant_model, spartan_client, spartan_model = build_llm_client()

    assistant_review = assistant_client.review(
        assistant_model,
        build_system_prompt("Assistant pass", "General engineering assistant reviewer"),
        review_input,
    )
    spartan_review = spartan_client.review(
        spartan_model,
        build_system_prompt("Spartan engineering pass", "Senior Python engineer named Spartan. Prioritize correctness, architecture, failure modes, compatibility, and maintainability."),
        review_input,
    )

    body = build_comment_body(pr, assistant_review, assistant_model, spartan_review, spartan_model)
    if existing_comment:
        gh.update_issue_comment(existing_comment["id"], body)
        print(f"Updated existing review comment {existing_comment['id']} for PR #{pr.number}")
    else:
        gh.create_issue_comment(pr.number, body)
        print(f"Created review comment for PR #{pr.number}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReviewError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
