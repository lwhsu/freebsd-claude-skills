# Authorship and Approval Decision Tree

## Determining `--author`

**Rule**: Always credit the patch submitter.

- **Using the reporter's patch as-is**: Set `--author="Name <email>"` to credit them.
- **Implementing independently** (your own fix): Use default author (no `--author`).

## Determining `Reported by:`

- **Using the reporter's patch**: Skip `Reported by:` — authorship already credits them.
- **NOT using the reporter's patch** (implementing independently): Add `Reported by:\tName <email>` to credit them for filing the bug/request.
- For `@FreeBSD.org` addresses: use just the account name (e.g., `se` not `Stefan Esser <se@FreeBSD.org>`).

## Determining `Approved by:`

Check the port's maintainer first:

```sh
make -V MAINTAINER
```

Decision tree:

1. **Maintainer is `ports@FreeBSD.org`** → No `Approved by:` needed (unmaintained port).
2. **We are the maintainer** → No `Approved by:` needed (our own port).
3. **Reporter is the maintainer** (emails match) → No `Approved by:` needed (maintainer submitted the change; set `--author` to credit them).
4. **Maintainer explicitly approved** (in bug comments or review) → `Approved by:\tName <email> (maintainer)`
5. **Trivial fix** (adding missing dependency, fixing obvious typo) → `Approved by:\tportmgr (blanket)`
6. **No approval yet** → Do not commit; wait for maintainer feedback.

## Summary table

| Scenario | `--author` | `Reported by:` | `Approved by:` |
|----------|------------|-----------------|-----------------|
| Reporter's patch, reporter is maintainer | Reporter | Skip | Skip |
| Reporter's patch, maintainer approved | Reporter | Skip | Maintainer |
| Reporter's patch, trivial fix | Reporter | Skip | portmgr (blanket) |
| Own fix, reporter filed bug | Default | Reporter | Maintainer or portmgr |
| Own fix, unmaintained port | Default | Reporter | Skip |
| Own fix, we are maintainer | Default | Reporter (if any) | Skip |
