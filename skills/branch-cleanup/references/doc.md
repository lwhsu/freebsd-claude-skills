# doc repo notes (doc.git)

## Reference branches — never candidates

- `main` only. The doc repo has no quarterly, stable, or releng branches.

Caution: work-branch names may look like release refs (e.g. lowercase
`2026q2-azure`) — those are ordinary work branches and ARE candidates. Only
branches actually present on the upstream `freebsd` remote count as reference
branches.

## Compare target

Always `TARGET=freebsd/main`.

## Third-party remotes

Doc trees may carry other contributors' forks for review. Local audit only,
never deletion candidates, never push targets.

## Supersession heuristics for NOT_MERGED

```sh
# Page still exists upstream? Doc tree reorganizations move files.
git cat-file -e "$TARGET:documentation/content/en/books/handbook/foo/_index.adoc" && echo EXISTS

# Did the same page change upstream since the branch was made?
git log --oneline "$base..$TARGET" -- documentation/content/en/books/handbook/foo/ | head
```

Typical obsolete patterns: the same doc fix was committed by someone else
(possibly reworded); the page was restructured or relocated so the branch's diff
no longer applies; translations regenerated. For relocated pages, diff the
branch's content against the file's new upstream location before judging.
