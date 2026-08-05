---
description: "Audit and clean up stale local and remote git branches by comparing file content against upstream, not commit hashes. This skill should be used when the user wants to tidy up branches, find which branches have already landed upstream, or prune personal fork remotes. Works in FreeBSD ports, src, and doc trees."
user_invocable: true
arguments: "[remote ...]"
---

# Branch Cleanup

Find branches whose work has already landed upstream and delete them, using **file content**
comparison rather than commit hashes.

## Why content, not hashes

Work rarely lands as a literal `cherry-pick`. It may be rebased, squashed, amended by a
committer, re-implemented by someone else, or superseded by a newer version. In all of
those cases the commit hash changes, so `git branch --merged`, `git cherry`, and ancestry
checks all report "not merged" for branches that are in fact obsolete. The only reliable
question is: *does this branch still propose any file content that upstream does not
already have?*

## Step 0 — Identify the repo and classify remotes

```sh
git remote -v
git remote get-url freebsd
```

The authoritative upstream is the remote named `freebsd`
(`git.freebsd.org` / `gitrepo.freebsd.org`). From its URL, read the matching
repo-specific notes **before Step 1** (reference branches and supersession
heuristics differ per repo):

| Upstream URL contains | Read |
|---|---|
| `ports.git` | `references/ports.md` |
| `src.git` | `references/src.md` |
| `doc.git` | `references/doc.md` |

Other repos: proceed with the generic procedure; ask the user what the reference
branches are.

Classify every other remote into:

- **Personal fork** — owned by the user (e.g. their GitHub forks). Eligible for cleanup.
- **Third-party** — someone else's fork added to review their work (common in src/doc).
  **Never candidates for deletion, local audit only.** Do not even enumerate their
  branches as cleanup candidates.

If ownership of a remote is not obvious from the URL, ask the user. If remotes were
given as arguments, clean only those; verify each is a personal fork first.
Default: all personal-fork remotes plus local branches.

Then sync:

```sh
git fetch --all --prune
```

`--prune` removes remote-tracking refs for branches already deleted on the remote, and
surfaces force-updates. Read the fetch output — a line like

```
 + 57b453fa8fb3...b8b05035f3a9 fcitx5 -> github/fcitx5  (forced update)
```

means a remote branch was rewritten, and a local branch of the same name may now be stale
in a way the name alone hides. Note these for Step 3.

## Step 1 — Enumerate candidates

```sh
git branch                       # local
git branch -r                    # remote-tracking
git worktree list                # branches checked out elsewhere
```

Exclude from the candidate set:

- The upstream remote's own branches (`freebsd/*`) — they are the reference, not work.
- Local branches that merely track an upstream reference branch (see the repo-specific
  notes for the exact list; `main` always qualifies). These are reference checkouts.
- Any branch listed by `git worktree list` as checked out in another worktree. Deleting
  those breaks that worktree. Never touch them.
- All branches on third-party remotes.
- `HEAD` pseudo-refs from `git branch -r` output.

## Step 2 — Classify by content

For each candidate ref, compute what the branch adds relative to its merge base, then ask
whether upstream already has that exact content. `TARGET` is normally `freebsd/main`;
branches based on another reference branch (e.g. a quarterly or `stable/*`) must be
compared against that branch instead — see the repo-specific notes.

```sh
TARGET=freebsd/main

check() {
  ref="$1"
  label="$2"
  base=$(git merge-base "$TARGET" "$ref" 2>/dev/null) || { echo "$label|NO_MERGE_BASE|-|-"; return; }
  files=$(git diff --name-only "$base" "$ref" 2>/dev/null)
  if [ -z "$files" ]; then
    echo "$label|EMPTY_DIFF_FROM_BASE|0|-"
    return
  fi
  nfiles=$(echo "$files" | wc -l | tr -d ' ')
  diffout=$(git diff "$TARGET" "$ref" -- $files 2>/dev/null)
  if [ -z "$diffout" ]; then
    echo "$label|FULLY_MERGED|$nfiles|-"
  else
    changed=$(git diff --name-only "$TARGET" "$ref" -- $files 2>/dev/null | wc -l | tr -d ' ')
    echo "$label|NOT_MERGED|$nfiles|$changed"
  fi
}
```

The key line is `git diff "$TARGET" "$ref" -- $files`: it restricts the comparison to the
files the branch actually touched, so unrelated upstream churn does not mask the answer.

Verdicts:

| Verdict | Meaning |
|---|---|
| `EMPTY_DIFF_FROM_BASE` | Branch changes nothing vs. its base. Dead. |
| `FULLY_MERGED` | Every file the branch touched is byte-identical upstream. Landed. |
| `NOT_MERGED` | Branch still proposes content upstream lacks. Needs judgment (Step 3). |
| `NO_MERGE_BASE` | No common ancestor — unrelated history. Investigate manually. |

Write the loop to a script file and run it; do **not** inline a multi-branch loop in a
one-off shell command. Two failure modes seen in practice:

- `set -e` aborts the whole run the moment `git merge-base` fails on one branch. Do not
  use `set -e` here; the `||` fallback in `check()` handles it.
- Unquoted `$f` in an ad-hoc `for f in $files` loop mangles output for branches touching
  several files, and can make `git cat-file -e` falsely report a path as missing.

## Step 3 — Judge the `NOT_MERGED` set

`NOT_MERGED` is not "keep". It means "a human must decide". Split it:

**Superseded / obsolete** — the branch's intent is already satisfied, differently.
Use the repo-specific heuristics from the reference file read in Step 0. Typical
patterns: someone else landed equivalent work; upstream moved past the branch's
version; the file/port was removed or relocated; the bug was fixed another way.

**Genuinely pending** — real unlanded work. Keep, and say why in the report.

Quote each judgment with the evidence command output. Do not assert "this path does not
exist upstream" from a scripted loop's output alone — re-run the check with an explicit,
quoted path before reporting it as fact.

**Stale-local vs. rewritten-remote** — for any force-update noticed in Step 0:

```sh
git merge-base --is-ancestor <local-branch> <remote>/<branch> && echo CONTAINED || echo DIVERGED
```

`DIVERGED` means the local branch holds a commit the rewritten remote branch dropped.
Surface it to the user explicitly; never resolve it silently in either direction.

## Step 4 — Report and wait

Present a table grouped by verdict, one row per branch: name, verdict, files touched, and
for `NOT_MERGED` a one-line reason. Group into:

- **A — landed** (`EMPTY_DIFF_FROM_BASE` / `FULLY_MERGED`): mechanically safe.
- **B — superseded**: safe, but the reasoning is a judgment call; show the evidence.
- **C — keep**: pending work.

**Stop here.** Deletion is irreversible for remote branches. Get explicit confirmation of
which groups to delete before running anything in Step 5. If the user approves "A and B",
that approval does not extend to C, to newly discovered branches, or to a re-run later.

## Step 5 — Delete

Batch per remote to keep it to one round trip each:

```sh
# local
git branch -D <branch1> <branch2> ...

# remote (personal forks only — never upstream, never third-party remotes)
git push <remote> --delete <branch1> <branch2> ...
```

`git branch -D` (not `-d`) is needed because these branches are, by construction, not
ancestors of `main` — that is the whole reason the content check exists.

## Step 6 — Verify

```sh
git fetch --all --prune
git branch -vv
git branch -r
```

Confirm what remains is exactly: reference branches, worktree branches, and group C.
Report the final list.

## Key rules

- Content comparison only. `git branch --merged` and hash matching are wrong here.
- Scope the diff to the files the branch touched, or upstream churn hides the answer.
- Reference branches, worktree branches, and third-party remotes are never candidates.
- `NOT_MERGED` requires human judgment, not automatic retention.
- Re-verify any surprising scripted result with a clean, explicitly quoted command before
  reporting it.
- No deletion without explicit per-group confirmation from the user.
- Never delete branches on the upstream `freebsd` remote or on third-party remotes.
