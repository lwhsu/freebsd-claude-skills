---
description: "MFC (Merge From Current, aka MFH) one or more commits from main into a FreeBSD ports quarterly branch (e.g. 2026Q3). This skill should be used when the user wants to merge a port commit to the quarterly branch, or mentions MFH, MFC to quarterly, or a quarter name like 2026Q3."
user_invocable: true
---

# FreeBSD ports MFC (quarterly branch)

Cherry-pick one or more commits from `main` into a ports quarterly branch, following the FreeBSD ports committers-guide convention (historically called "MFH").

## Invocation

```
/port-mfc <hash1> [hash2 ...] [-q <quarter>]
```

- `<hash>` — commit hash(es) on `main` to merge (space-separated, oldest first)
- `-q <quarter>` — target quarterly branch, e.g. `2026Q3`; if omitted, determined per Step 0

## Environment assumptions

- A git worktree exists per quarterly branch (e.g. `../freebsd-ports-2026Q3` for branch `2026Q3`). Discover via `git worktree list`.
- The upstream remote is named `freebsd`.
- Unlike `releng/*` branches in src, merging to a ports quarterly branch needs **no separate approval** (committers-guide, in effect since 2020-11-30).

## Step 0 — Determine target quarter(s)

For each hash, if `-q` was not given:

1. Read the `MFC:` trailer from the commit message:
   ```sh
   git show <hash> --no-show-signature --format="%B" -s | grep -i "^MFC:"
   ```
2. Find the latest quarterly branch that actually exists:
   ```sh
   git branch -a --no-color | grep -oE '(remotes/freebsd/)?[0-9]{4}Q[0-9]$' | sed 's#.*/##' | sort -V | tail -1
   ```
3. **If the `MFC:` trailer's quarter is not the latest quarterly branch, stop and warn the user before proceeding.** MFC'ing to an older quarter is very likely a mistake (stale trailer, or the commit should target the current quarter instead). Only continue against the older quarter after the user explicitly confirms that's intentional.
4. If there is no `MFC:` trailer, ask the user which quarter to target — suggest the latest quarterly branch as the default.

## Step 1 — Pre-flight checks

For each hash × each target quarter:

```sh
# a. Confirm the hash exists and is reachable from freebsd/main
git merge-base --is-ancestor <hash> freebsd/main && echo ok

# b. Confirm it hasn't already been MFC'd
git -C <worktree> log <quarter> --grep="cherry picked from commit <hash>" --oneline
```

Skip (with a note) any quarter where the commit is already present.

## Step 2 — Update the worktree

```sh
git -C <worktree> fetch freebsd <quarter>
git -C <worktree> merge --ff-only freebsd/<quarter>
```

Use `--ff-only`, not rebase — a quarterly-branch worktree should never have local-only commits. If the fast-forward fails, stop and investigate rather than forcing.

## Step 3 — Cherry-pick

```sh
git -C <worktree> cherry-pick -x <hash>
```

Repeat for each hash targeting that quarter, oldest first. Quarterly-branch MFCs are not squashed by default (unlike stable/src MFCs) — only squash multiple commits if the user explicitly asks.

## Step 4 — Conflict handling

If `cherry-pick` reports a conflict:

1. List the conflicting files: `git -C <worktree> diff --name-only --diff-filter=U`
2. **Auto-resolve only this narrow case**: the conflict is confined to a plain version-bump — `Makefile` (`PORTVERSION`/`DISTVERSION`/`PORTREVISION` lines only) and `distinfo` (checksums/timestamp only), nothing else conflicting. Take the incoming (cherry-picked) side for those lines/files wholesale — they came from the same upstream commit, so the pairing is already consistent by construction; no regeneration needed. Optionally sanity-check with `make checksum` (verifies the distfile against `distinfo`; do **not** use `make makesum`, which regenerates/overwrites `distinfo` instead of verifying it). Then `git add` the resolved files and continue.
3. **Anything else** — differing Makefile logic, patch-content conflicts, plist conflicts, or a version-bump conflict mixed with other changes — never auto-resolve. Read the conflicting hunks (`git -C <worktree> diff`) and what changed on the quarterly branch (`git -C <worktree> log -10 -- <file>`), formulate a resolution plan, and present it to the user for confirmation before applying.
4. `git -C <worktree> cherry-pick --continue`

## Step 5 — Verification (TODO, not yet implemented)

This step is currently a no-op. It should eventually invoke the `/poudriere` skill for a real test build in the quarterly-branch worktree — packages built off the quarterly branch are what `pkg install` serves to users, so this matters more here than for a `main`-branch commit. Until that's wired up, verification is left to the user.

## Step 6 — Output (no auto-push)

```
MFC complete. Review the commit(s), then push when ready.

  2026Q3  <new-hash>  <subject>

Push command:
  git -C <worktree> push freebsd HEAD:<quarter>

If push fails due to a race:
  git -C <worktree> fetch freebsd <quarter>
  git -C <worktree> merge --ff-only freebsd/<quarter>
  git -C <worktree> push freebsd HEAD:<quarter>
```

**Never execute the push.** The user always confirms and runs it themselves.

## Key rules

- Always use `git cherry-pick -x` — the `(cherry picked from ...)` line is mandatory.
- `security/vuxml` commits are **never** MFC'd to quarterly branches. `pkg audit`'s vulnerability database is built from `main`, independent of quarterly-branch content — only cherry-pick the port-fix commit(s) that carry a `Security:`/`MFC:` trailer, not the VuXML commit itself.
- No squash by default; only squash multiple commits if the user asks.
- Do not strip trailers (`Security:`, `MFC:`, `PR:`, etc.) from the MFC'd commit message.
- Anything that writes to the upstream `freebsd` remote is always left for the user to run.
