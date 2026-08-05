# Ports repo notes (ports.git)

## Reference branches — never candidates

- `main`
- Current quarterly branch: `YYYYQn`, uppercase `Q` (e.g. `2026Q3`).
- **Expired** quarterly branches (older than the current quarter, e.g. a local
  `2026Q2` after Q3 started) are legitimate deletion candidates — flag them,
  do not assume.

## Compare target

- Branches based on `main`: `TARGET=freebsd/main`.
- Branches based on a quarterly (MFH work): compare against that quarterly
  (`freebsd/2026Q3`), not `main` — versions on main are usually ahead, which
  would mask a landed MFH.

## Supersession heuristics for NOT_MERGED

```sh
# Does the port exist upstream at all now?
git cat-file -e "$TARGET:devel/foo/Makefile" && echo EXISTS

# Is upstream's version newer than the branch's?
git show "$TARGET:devel/foo/Makefile" | grep -E '^(PORT|DIST)VERSION|^PORTREVISION'
git show "$ref:devel/foo/Makefile"    | grep -E '^(PORT|DIST)VERSION|^PORTREVISION'

# Was the port deprecated / scheduled for removal upstream?
git show "$TARGET:devel/foo/Makefile" | grep -E '^(DEPRECATED|EXPIRATION_DATE)'
```

Typical obsolete patterns: someone else added the same new port; upstream shipped a
newer version than the branch proposed; the port was removed from the tree
(check `MOVED`); the bug the branch fixed was fixed another way.
