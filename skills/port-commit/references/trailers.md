# FreeBSD Ports Commit Trailer Reference

Trailers are appended after the commit body, before `Co-Authored-By`. Each trailer uses **tab characters** after the colon for alignment.

## Trailer formats

### PR (Bugzilla ticket)

```
PR:		<bug-number>
```

Example: `PR:\t\t123456`

Two tabs after `PR:` for alignment.

### Reported by

```
Reported by:	<Full Name> <email>
```

Example: `Reported by:\tJohn Doe <john@example.com>`

For `@FreeBSD.org` addresses, use just the account name: `Reported by:\tse`

### Approved by

```
Approved by:	<approver>
```

Examples:
- `Approved by:\tJohn Doe <john@example.com> (maintainer)`
- `Approved by:\tportmgr (blanket)`

### Differential Revision (Phabricator)

```
Differential Revision:	<full URL>
```

Example: `Differential Revision:\thttps://reviews.freebsd.org/D55591`

### Fixes (referencing a previous commit)

```
Fixes:		<short-hash> <title of commit being fixed>
```

Example: `Fixes:\t\t44f2066f7589 devel/py-commoncode: update to 32.2.1`

Two tabs after `Fixes:` for alignment.

### Security (VuXML VID)

```
Security:	<VID-UUID>
```

Only for commits that fix security vulnerabilities. The VID is the UUID from the VuXML entry.

### MFC (Merge From Current)

```
MFC:		<YYYYQN>
```

Example: `MFC:\t\t2026Q1`

Two tabs after `MFC:`. Only for security updates that need backporting to quarterly branches.

## Ordering

Trailers should appear in this order:

1. `PR:`
2. `Reported by:`
3. `Approved by:`
4. `Security:`
5. `MFC:`
6. `Differential Revision:`
7. `Fixes:`

Then a blank line, followed by:

```
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

## Complete example

```
devel/py-foo: Update to 1.2.3

PR:		123456
Reported by:	John Doe <john@example.com>
Approved by:	Jane Smith <jane@example.com> (maintainer)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

## Notes

- Check `.hooks/prepare-commit-msg` in the ports tree for the canonical trailer template.
- Use actual tab characters, not spaces or `\t` escape sequences.
- When fixing a previous commit, get the PR number from that commit's own message body:
  ```sh
  git log --no-show-signature --format="%s%n%b" -1 <hash>
  ```
