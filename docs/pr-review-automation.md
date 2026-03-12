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

Set this repository secret to enable AI review generation:

- `OPENAI_API_KEY`

If the secret is not configured, the workflow exits cleanly and logs that advisory review was skipped.

Optional repository variables:

- `ASSISTANT_REVIEW_MODEL` default: `gpt-4.1-mini`
- `SPARTAN_REVIEW_MODEL` default: `gpt-4.1`
- `OPENAI_BASE_URL` default: `https://api.openai.com/v1`

If you use an OpenAI-compatible provider, set both `OPENAI_API_KEY` and `OPENAI_BASE_URL`.

## Files

- `.github/workflows/pr-review.yml`
- `.github/scripts/pr_review.py`
- `.github/review-instructions.md`

## Notes

- Keep the rubric in `.github/review-instructions.md` concise and repo-specific.
- The script uses Python standard library only.
- `/review` support is included now so label-based retriggers can be added later without changing the core review flow.
