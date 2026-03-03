---
description: "Process a FreeBSD Phabricator review for a port. This skill should be used when the user provides a Phabricator review URL or number (D12345), or asks to apply a review from reviews.freebsd.org."
user_invocable: true
arguments: "<review-id>"
---

# Phabricator Review Processing Workflow

Apply a port change from a Phabricator review (reviews.freebsd.org).

## Inputs

- `review-id` — the Phabricator review ID (e.g., `D12345` or just `12345`)

## Procedure

### 1. Fetch the raw diff

```sh
fetch -qo - 'https://reviews.freebsd.org/D<N>?download=true'
```

Review the diff to understand what changes are being made.

### 2. Determine the port and version

From the diff or review description, identify:
- The target `category/portname`
- The new version (if it's an update)

### 3. Create the branch

```sh
git checkout main
git pull
git checkout -b claude/update-<portname>-<version>
```

### 4. Apply the diff

Apply the changes from the diff. This may involve:
- Editing the Makefile
- Updating distinfo
- Adding/modifying/removing patches
- Updating pkg-plist

### 5. Determine authorship and approval

Same rules as Bugzilla tickets (see `port-bug/references/author-rules.md`):
- If the submitter is the maintainer: set `--author` to credit them, no `Approved by:` needed
- Otherwise: follow standard maintainer approval rules

### 6. Test with poudriere

Use the `/poudriere` skill. Must be on the feature branch.

### 7. Commit

Use the `/port-commit` skill. Include the `Differential Revision:` trailer:

```
Differential Revision:\thttps://reviews.freebsd.org/D<N>
```

### 8. Switch back

```sh
git checkout main
```

## Notes

- No Conduit API token is typically configured — the user handles closing/updating the review status on Phabricator manually.
- The raw diff URL format is `https://reviews.freebsd.org/D<N>?download=true`.
