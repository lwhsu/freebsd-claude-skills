---
description: "Handle a FreeBSD port security advisory. This skill should be used when the user needs to create a VuXML entry and update a port for a security vulnerability, or mentions CVE, security advisory, or VuXML."
user_invocable: true
---

# Security Advisory Workflow

Create a VuXML entry and update a port to fix a security vulnerability.

## Procedure

### 1. Create the branch

```sh
git checkout main
git pull
git checkout -b claude/vuxml-<product>-<YYYY-MM-DD>
```

Use today's date or the advisory date.

### 2. Create the VuXML entry

Edit `security/vuxml/vuln.xml` to add a new entry. See `references/vuxml-format.md` for the XML template and field descriptions.

Key fields:
- `vid` — a new UUID (generate with `uuidgen`)
- `topic` — short description of the vulnerability
- `affects` — package name and vulnerable version ranges
- `references` — CVE IDs, advisory URLs
- `dates` — discovery and entry dates

### 3. Commit the VuXML entry FIRST

The VuXML commit must come before the port update commit.

```
security/vuxml: Document <Product> Security Advisory YYYY-MM-DD
```

### 4. Update the port

Use the `/port-update` skill for the actual version bump and testing.

### 5. Commit the port update with security trailers

The port update commit needs two extra trailers beyond the usual ones:

```
Security:\t<VID>
MFC:\t\tYYYYQN
```

Where:
- `<VID>` is the UUID from the VuXML entry
- `YYYYQN` is the current quarterly branch (e.g., `2026Q1`)

Use the `/port-commit` skill and include these additional trailers.

### 6. Commit ordering

The final branch should have commits in this order:
1. VuXML entry
2. Port update (weekly/latest)
3. Port update for LTS branch (if applicable)

### 7. Switch back

```sh
git checkout main
```

## Tips

- When `git cherry-pick --no-gpg-sign` fails because gpgsign is set in git config, use `git -c commit.gpgsign=false cherry-pick` instead.
- To non-interactively reword just the first commit in a series:
  ```sh
  GIT_SEQUENCE_EDITOR="sed -i '' '1s/^pick/reword/'" GIT_EDITOR="printf 'new subject\n' >" git -c commit.gpgsign=false rebase -i HEAD~N
  ```
