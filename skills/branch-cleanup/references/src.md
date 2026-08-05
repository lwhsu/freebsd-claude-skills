# src repo notes (src.git)

## Reference branches — never candidates

- `main`
- `stable/*` (e.g. `stable/14`, `stable/15`)
- `releng/*`

These are often checked out in dedicated worktrees (`git worktree list` catches
them too).

## Compare target

- Branches based on `main`: `TARGET=freebsd/main`.
- MFC branches based on a stable branch: compare against that branch
  (`freebsd/stable/14`), not `main`.

## Third-party remotes

src trees commonly carry several remotes for other contributors' forks (added to
review or test their work). They are read-only: local audit only, never deletion
candidates, never push targets. When in doubt whether a remote is the user's own
fork, ask.

## Supersession heuristics for NOT_MERGED

```sh
# File still exists upstream? (code moves are common — check git log --follow)
git cat-file -e "$TARGET:sys/dev/foo/foo.c" && echo EXISTS

# Did the same area change upstream since the branch was made?
git log --oneline "$base..$TARGET" -- sys/dev/foo/ | head

# For MFC branches: did the commit reach the stable branch another way?
git log --oneline "freebsd/stable/14" --grep='cherry picked from' -- sys/dev/foo/ | head
```

Typical obsolete patterns: the fix landed via a different commit or a larger
rework; the file was moved/renamed (diff against the new location); the change
was committed by someone else with review trailers; an MFC already reached the
stable branch.
