---
description: "MFC (Merge From Current) one or more commits from main to FreeBSD stable branches. This skill should be used when the user wants to cherry-pick a commit from main to stable/14, stable/15, or other supported branches."
user_invocable: true
---

# FreeBSD src MFC

Cherry-pick one or more commits from `main` into supported stable branches, following FreeBSD project MFC conventions.

## Invocation

```
/src-mfc <hash1> [hash2 ...] [-b <version>]
```

- `<hash>` — commit hash(es) on `main` to MFC (space-separated, oldest first)
- `-b <version>` — target a specific major version, e.g. `-b 15` means `stable/15`; repeatable; defaults to all currently supported stable branches with planned future releases

## Environment assumptions

This skill assumes:
- A git worktree exists per stable branch (e.g. `../freebsd-src-14` for `stable/14`)
- The upstream remote is named `freebsd`
- The FreeBSD doc repo is available locally

Paths are user-specific — adapt as needed. The skill will discover worktrees via `git worktree list`.

## Step 0 — Determine target branches

Skip this step if `-b` is given.

Read two files from the local doc repo:

**A. Supported branches with active EOL** — `<doc-repo>/website/content/en/security/_index.adoc`
```
grep lines matching "^|stable/"
→ parse branch name + Expected EoL date
→ keep only branches whose EoL is in the future
```

**B. Branches with planned future releases** — `<doc-repo>/website/content/en/releng/_index.adoc`
```
find the [[schedule]] section table
→ extract upcoming release names (e.g. "FreeBSD 15.1", "FreeBSD 14.5")
→ collect the set of major version numbers with at least one future release
```

**C. Intersection** — default targets = branches from A whose major version appears in B

Rationale: a stable branch near EOL with no future release planned (e.g. stable/13 after 13.5 shipped) is only relevant for security fixes, not general MFCs.

If `-b` specifies a branch outside the supported set, warn the user but proceed.

## Step 1 — Pre-flight checks

For each hash × each target branch:

```sh
# a. Confirm hash exists on main
git log --oneline -1 <hash>

# b. Check MFC-after period (parse from commit message; warn if not yet due, do not block)
git show <hash> --format="%B" | grep "MFC after:"

# c. Confirm not already MFC'd
git -C <worktree> log <branch> --grep="<hash>" --oneline
git -C <worktree> log <branch> --grep="cherry picked from commit <hash>" --oneline
```

Report findings. Skip branches where the commit is already present.

## Step 2 — Update worktrees

```sh
git -C <worktree> fetch freebsd <branch>
git -C <worktree> rebase freebsd/<branch>
```

Fetch all target worktrees before cherry-picking.

## Step 3a — Single commit

```sh
git -C <worktree> cherry-pick -x <hash>
```

Repeat for each target branch.

## Step 3b — Multiple commits (squash)

For each target branch:

```sh
# 1. Create temp branch from the stable branch
git -C <worktree> checkout -b mfc-tmp

# 2. Cherry-pick all hashes in order (oldest first)
for h in <hash1> <hash2> ...; do
    git -C <worktree> cherry-pick -x $h
done

# 3. Squash into one commit interactively
git -C <worktree> rebase -i freebsd/<branch>
# mark all commits after the first as 'squash'
```

Construct a suggested squashed commit message:
- Subject: combine subjects of all original commits
- Body: include all original bodies, deduplicated
- Remove duplicate `MFC after:` lines
- Retain all `(cherry picked from commit ...)` lines

**Pause**: present the draft message to the user for confirmation/editing before committing.

After user confirms:
```sh
git -C <worktree> commit --amend   # apply confirmed message
git -C <worktree> push freebsd HEAD:<branch>
git -C <worktree> checkout <branch>
git -C <worktree> branch -d mfc-tmp
```

## Step 4 — Conflict handling

If `cherry-pick` reports conflicts:

1. Read the conflicting hunks: `git -C <worktree> diff`
2. Check what changed on the stable branch: `git -C <worktree> log -10 -- <conflicting-file>`
3. Formulate a resolution plan and present it to the user for confirmation
4. After confirmation, apply the resolution
5. `git -C <worktree> cherry-pick --continue`

Never auto-resolve conflicts.

## Step 5 — Output (no auto-push)

```
MFC complete. Review the commits, then push when ready.

  stable/15  <new-hash>  <subject>
  stable/14  <new-hash>  <subject>

Push commands:
  git -C <worktree-15> push freebsd HEAD:stable/15
  git -C <worktree-14> push freebsd HEAD:stable/14

If push fails due to a race:
  git -C <worktree> pull --rebase
  git -C <worktree> push freebsd HEAD:<branch>
```

**Never execute the push.** The user always confirms and runs it themselves.

## Key rules

- Always use `git cherry-pick -x` — the `(cherry picked from ...)` line is mandatory
- Vendor import merge commits: use `git cherry-pick -x -m 1 <hash>`
- MFC to `releng/*` requires re@ approval and is not handled by this skill
- Do not strip `Sponsored by:`, `Reviewed by:`, or `Differential Revision:` from MFC commit messages
- `MFC after:` lines may be left as-is in single-commit MFCs; remove duplicates in squashed MFCs
- Anything that writes to the upstream `freebsd` remote is always left for the user to run
