# Issue tracker: GitHub

Issues and specs for this repository live in GitHub Issues at `kenneth-liao/youtube-data-tools`. Use the best available GitHub interface; use the `gh` CLI as the portable fallback. Run commands inside this clone so the remote identifies the correct repository.

## Conventions

- **Create:** `gh issue create --title "..." --body-file -`
- **Read:** `gh issue view <number> --comments`, including labels, assignees, state, relationships, and linked pull requests as needed
- **List:** `gh issue list --state open --json number,title,body,labels,assignees,comments`
- **Comment:** `gh issue comment <number> --body-file -`
- **Label:** `gh issue edit <number> --add-label "..."` or `--remove-label "..."`
- **Close:** post the explanation first, then run `gh issue close <number>`

Use quoted heredocs or `--body-file` for Markdown so the shell cannot expand its contents.

## Claiming implementation work

Assignment makes active ownership visible. A deterministic issue branch and worktree provide local exclusion.

- **Check:** inspect issue state, assignees, linked open pull requests, and any existing deterministic branch/worktree
- **Claim:** `gh issue edit <number> --add-assignee @me`
- **Release:** `gh issue edit <number> --remove-assignee @me`
- **Active-work signals:** an assignee, open linked pull request, or deterministic issue branch/worktree

Assignment is cooperative, not a distributed lock. Do not start duplicate work merely because the current account is the assignee; inspect existing work and require an explicit resume or handoff.

## Pull requests

- Create a pull request from the deterministic issue branch when it is ready for review.
- Read with `gh pr view <number> --comments` and `gh pr diff <number>`.
- Add `Closes #<number>` to the pull-request body to close the issue on merge.

Pull requests are not a triage request surface.

## Relationships and blockers

Use GitHub's native sub-issue and dependency relationships when available. Otherwise, record durable `Parent:` and `Blocked by:` references in issue bodies or comments. Work is on the implementation frontier only when it is open, ready, unblocked, unassigned, and has no active linked pull request.
