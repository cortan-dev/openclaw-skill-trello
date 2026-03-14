# PR review automation

This repo can post one consolidated advisory review comment for each PR head SHA.

## What it does

On supported PR events, the workflow runs two review passes:

1. Assistant pass
2. Spartan engineering pass

Both passes read `.github/review-instructions.md` first when it exists, then review the PR diff, changed file contents, and current check status.

The comment format is:

- Summary
- Blocking issues
- Non-blocking improvements
- Test assessment
- Merge recommendation

The workflow is advisory only. It does not block merges.

## Triggers

The workflow runs on:

- `pull_request` `opened`
- `pull_request` `synchronize`
- `pull_request` `reopened`
- `pull_request` `ready_for_review`
- `issue_comment` with exact body `/review` on a PR from a trusted repo actor (`OWNER`, `MEMBER`, or `COLLABORATOR`)
- `workflow_dispatch` with a PR number

Draft PRs are skipped until they are marked ready for review, unless `/review` or `workflow_dispatch` is used.

## Duplicate suppression

The workflow writes a hidden marker with the PR head SHA into its comment.

- If the same SHA is seen again from normal PR events, it skips posting a duplicate comment.
- If `/review` or `workflow_dispatch` is used for the same SHA, it updates the existing comment for that SHA.
- Untrusted `/review` comments are ignored.
- When a new commit is pushed, the head SHA changes and a fresh review comment is posted.

## Required configuration

Set at least one LLM credential as a repository secret to enable AI review generation.

### Recommended setup (dual provider)

| Secret / Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` (secret) | Anthropic API key — used for the Cortan assistant pass |
| `OPENAI_API_KEY` (secret) | Gemini API key — used for the Spartan engineering pass |
| `OPENAI_BASE_URL` (variable) | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `ASSISTANT_REVIEW_MODEL` (variable) | `claude-sonnet-4-5` (default) |
| `SPARTAN_REVIEW_MODEL` (variable) | `gemini-2.5-flash` (default) |

### Single provider fallback

If only one key is set, both passes use that provider.

### OpenAI-only setup

Set `OPENAI_API_KEY` and optionally `OPENAI_BASE_URL` (defaults to `https://api.openai.com/v1`).

If no credentials are configured, the workflow exits cleanly and logs that advisory review was skipped.

## Files

- `.github/workflows/pr-review.yml`
- `.github/scripts/pr_review.py`
- `.github/review-instructions.md`

## Notes

- Keep the rubric in `.github/review-instructions.md` concise and repo-specific.
- The script uses Python standard library only.
- `/review` support is included now so label-based retriggers can be added later without changing the core review flow.
