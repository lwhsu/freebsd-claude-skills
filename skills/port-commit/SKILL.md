---
description: "Format and create a FreeBSD ports commit with proper trailers. This skill should be used when the user asks to commit port changes, or after a successful poudriere build."
user_invocable: true
---

# FreeBSD Ports Commit Formatting

Create a properly formatted commit for the FreeBSD ports tree.

## Procedure

### 1. Determine the maintainer

```sh
cd <ports-tree>/<category>/<portname>
make -V MAINTAINER
```

### 2. Determine the commit subject

Format depends on the change type:
- Version update: `category/portname: Update to X.Y.Z`
- Bug fix: `category/portname: Fix <description>`
- New port: `category/portname: Add <short-description>`
- Adding rc script: `category/portname: Add rc script`
- Security update: `category/portname: Update to X.Y.Z` (with extra trailers)

### 3. Determine authorship

If someone else submitted the patch:
```sh
git commit --no-gpg-sign --author="Name <email>" ...
```

If implementing the change yourself: use default author.

### 4. Assemble trailers

Trailers use **tab characters** after the colon. See `references/trailers.md` for the complete reference.

Common trailers (in order):

| Trailer | When to include |
|---------|----------------|
| `PR:` | Bug ticket number |
| `Reported by:` | Bug reporter (when NOT using their patch) |
| `Approved by:` | Maintainer approval or portmgr blanket |
| `Security:` | VuXML VID (security updates only) |
| `MFC:` | Quarterly branch (security updates only) |
| `Differential Revision:` | Phabricator review URL |
| `Fixes:` | Hash + title of commit being fixed |

### 5. Approval rules

- **Maintainer is `ports@FreeBSD.org`**: no `Approved by:` needed
- **Maintainer approved**: `Approved by:\tName <email> (maintainer)`
- **Trivial fix**: `Approved by:\tportmgr (blanket)`
- **Reporter is the maintainer**: no `Approved by:` needed (authorship implies it)
- **We are the maintainer**: no `Approved by:` needed

### 6. Create the commit

Always use a HEREDOC for the message to preserve formatting:

```sh
git commit --no-gpg-sign -m "$(cat <<'EOF'
category/portname: Update to X.Y.Z

PR:\t\t123456
Approved by:\tJohn Doe <john@example.com> (maintainer)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

**Important**: The literal `\t` above represents actual tab characters in the commit message. Use actual tabs, not the escape sequence.

### 7. Verify

```sh
git log -1
```

Check that the subject line, trailers, and authorship are correct.

### 8. Switch back to main

```sh
git checkout main
```

## Tips

- Commit without GPG signature (`--no-gpg-sign`) — the user will amend with their signature later.
- For `@FreeBSD.org` addresses in `Reported by:`, use just the account name (e.g., `se` not `Stefan Esser <se@FreeBSD.org>`).
- Trailers go after the commit body, before `Co-Authored-By`.
- When fixing a previous commit, get the PR number from that commit's message body: `git log --no-show-signature --format="%s%n%b" -1 <hash>`
