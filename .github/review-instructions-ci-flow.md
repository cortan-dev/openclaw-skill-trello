# PR review flow for agents

When Spartan or Cortan works on a PR in this repo, the following steps are mandatory before declaring a PR merge-ready.

## Required steps (in order)

1. **CI pass** — confirm `CI` workflow conclusion is `success` for the PR head SHA
2. **PR review automation pass** — confirm `PR review automation` workflow ran and posted a comment (or ran manually via `/review`)
3. **Spartan manual review** — Spartan reads the diff and posts a review comment on the PR
4. **Cortan manual review** — Cortan reads the diff and posts a review comment on the PR

## How to check CI

```bash
curl -s "https://api.github.com/repos/cortan-dev/openclaw-skill-trello/actions/runs?branch=BRANCH_NAME" \
  -H "Authorization: token TOKEN" | python3 -c "import sys,json; [print(r['name'], r['conclusion']) for r in json.load(sys.stdin)['workflow_runs']]"
```

## Declaration

Only after all 4 steps are confirmed can a PR be declared merge-ready. Report status of each step explicitly when reporting back.
