---
description: "Process a FreeBSD ports GitHub pull request. This skill should be used when the user provides a GitHub PR URL or number (e.g., https://github.com/freebsd/freebsd-ports/pull/548 or just 548), or asks to apply a PR from the freebsd/freebsd-ports mirror."
user_invocable: true
arguments: "<pr-url-or-number>"
---

# GitHub Pull Request Processing Workflow

Apply a port change from a GitHub PR against the freebsd/freebsd-ports mirror.

## Inputs

- `pr-url-or-number` — the GitHub PR URL (e.g., `https://github.com/freebsd/freebsd-ports/pull/548`) or just the number (`548`)

## Procedure

### 1. Update the tree first

```sh
git checkout main
git pull
```

### 2. Fetch the PR metadata

Use the GitHub API (no auth needed for public repos):

```sh
fetch -qo - 'https://api.github.com/repos/freebsd/freebsd-ports/pulls/<N>'
```

Extract:
- `title` — the PR title
- `state` — open/closed
- `body` — description (may include `Sponsored-by:` lines)
- `user.login` — submitter's GitHub login
- `html_url` — canonical PR URL

See `references/github-api.md` for details.

### 3. Triage

Skip if:
- `state` is `closed` or `merged` — already handled
- The port is already updated past the requested version in the tree

Check the current port in the tree:

```sh
make -C <ports-tree>/<category>/<portname> -V DISTVERSION
```

### 4. Read PR comments

Check for maintainer approval or correction comments:

```sh
fetch -qo - 'https://api.github.com/repos/freebsd/freebsd-ports/issues/<N>/comments'
```

Also check review comments:

```sh
fetch -qo - 'https://api.github.com/repos/freebsd/freebsd-ports/pulls/<N>/comments'
```

Read all comments before deciding on an approach — a later comment may correct or supersede the original.

### 5. Fetch the diff

```sh
fetch -qo - 'https://github.com/freebsd/freebsd-ports/pull/<N>.diff'
```

Review the diff to understand what changes are being made.

### 6. Get the submitter's email

The PR commit metadata is more reliable than the GitHub user profile:

```sh
fetch -qo - 'https://api.github.com/repos/freebsd/freebsd-ports/pulls/<N>/commits'
```

Extract `commit.author.name` and `commit.author.email` from the first commit.

If the email is a GitHub noreply address (`<login>@users.noreply.github.com`), try the GitHub user API:

```sh
fetch -qo - 'https://api.github.com/users/<login>'
```

Use `name` and `email` fields if available.

### 7. Create the branch

```sh
git checkout -b claude/pr<N>-<short-description>
# For version updates:
git checkout -b claude/pr<N>-update-<portname>-<version>
```

### 8. Apply the diff

Apply the patch from the diff. Use `git apply` or `patch`:

```sh
fetch -qo /tmp/pr<N>.diff 'https://github.com/freebsd/freebsd-ports/pull/<N>.diff'
git apply /tmp/pr<N>.diff
```

If `git apply` fails (e.g., context mismatch), try:

```sh
patch -p1 < /tmp/pr<N>.diff
```

### 9. Determine authorship and approval

See `port-bug/references/author-rules.md` for the complete decision tree.

**Important**: Check if the submitter is the port's maintainer:

```sh
make -C <ports-tree>/<category>/<portname> -V MAINTAINER
```

Compare against the commit author email fetched in step 6.

Quick summary:
- **Using submitter's diff as-is**: `--author="Name <email>"` (skip `Reported by:`)
- **Submitter IS the maintainer**: no `Approved by:` needed
- **Maintainer approved in comments**: `Approved by:\tName <email> (maintainer)`
- **Trivial fix, unmaintained port**: `Approved by:\tportmgr (blanket)`

### 10. Test with poudriere

Use the `/poudriere` skill. Must be on the feature branch.

### 11. Commit

Use the `/port-commit` skill. Include the `GitHub PR:` trailer:

```
GitHub PR:		https://github.com/freebsd/freebsd-ports/pull/<N>
```

If the PR body contains a `Sponsored-by:` line, include it as a `Sponsored by:` trailer:

```
Sponsored by:	Framework Computer Inc
```

Full example commit message:

```
sysutils/framework-system: Update to 0.6.4

GitHub PR:		https://github.com/freebsd/freebsd-ports/pull/548
Sponsored by:	Framework Computer Inc

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### 12. Close the PR

After the commit is pushed by the user, comment on the PR to close the loop:

```sh
fetch -qo - --post-data '{"body":"Thank you! Applied as <short-hash> (https://cgit.freebsd.org/ports/commit/?id=<full-hash>).\n\nClosing as the change has been committed to the ports tree."}' \
  -H 'Authorization: token <GH_TOKEN>' \
  'https://api.github.com/repos/freebsd/freebsd-ports/issues/<N>/comments'
```

Since the freebsd-ports GitHub repo is a read-only mirror, PRs cannot be merged through GitHub — they must be closed manually by the user via the GitHub web UI or `gh pr close <N> --repo freebsd/freebsd-ports`.

### 13. Switch back

```sh
git checkout main
```

## Notes

- The freebsd/freebsd-ports GitHub repo is a **read-only mirror** of the SVN/git tree — PRs cannot be merged via GitHub.
- GitHub API rate limit: 60 requests/hour unauthenticated. Set `GH_TOKEN` env var for higher limits.
- If the submitter has no public email, prefer the commit author email from step 6 over constructing a noreply address.
