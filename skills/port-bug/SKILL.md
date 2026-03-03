---
description: "Process a FreeBSD Bugzilla ticket for a port. This skill should be used when the user provides a bug number, asks to fix a port bug, or wants to process a Bugzilla ticket."
user_invocable: true
arguments: "<bug-number>"
---

# Bugzilla Ticket Processing Workflow

Process a FreeBSD Bugzilla ticket (bugs.freebsd.org) for a port update, bug fix, or feature request.

## Inputs

- `bug-number` — the Bugzilla ticket number (e.g., `123456`)

## Procedure

### 1. Update the tree first

```sh
git checkout main
git pull
```

### 2. Fetch the ticket

Use the `bugzilla` CLI. See `references/bugzilla-cli.md` for command details.

```sh
bugzilla query --bug_id <N> --outputformat '%{id} %{status} %{summary}'
```

Fetch full details including comments (the CLI supports `%{comments}`).

### 3. Read ALL comments

**Critical**: Read every comment before deciding on an approach. Maintainers sometimes post corrections in later comments (e.g., "Approved (the second patch, sorry)"). The final comment is authoritative.

### 4. Triage

Skip the ticket if:
- Status is already CLOSED
- `maintainer-feedback` flag is `?` (pending) and no patch is attached — wait for maintainer response
- The port was already updated in the tree to the requested version

Check the current port in the tree — has it already been updated past what the ticket requests?

### 5. Determine the approach

**If a patch is attached:**
- Fetch the attachment (see `references/bugzilla-cli.md`)
- When multiple attachments exist, check `is_obsolete` — use only the non-obsolete (latest) one
- Review the patch visually and apply it
- No need to run `make makesum` ourselves — poudriere verifies checksums

**If it's a version update request without a patch:**
- Use the `/port-update` skill for the version bump workflow

**If it's a bug report (not an update):**
- Verify the bug still exists on the current version before fixing
- Build the unpatched version to confirm the problem

### 6. Create the branch

```sh
git checkout -b claude/bug<number>-<short-description>
# For updates:
git checkout -b claude/bug<number>-update-<portname>-<version>
```

### 7. Apply the fix

Apply the patch or make the necessary changes.

### 8. Determine authorship and approval

See `references/author-rules.md` for the complete decision tree.

Quick summary:
- **Using reporter's patch as-is**: `--author="Name <email>"` (skip `Reported by:`)
- **Implementing independently**: add `Reported by:` trailer
- **Maintainer approved**: add `Approved by:\tName <email> (maintainer)`
- **Reporter IS the maintainer**: no `Approved by:` needed
- **Trivial fix**: `Approved by:\tportmgr (blanket)`

### 9. Test with poudriere

Use the `/poudriere` skill. Must be on the feature branch.

### 10. Commit

Use the `/port-commit` skill. Include the `PR:` trailer:

```
PR:\t\t<bug-number>
```

### 11. Close the ticket

After the commit is pushed (by the user):

```sh
bugzilla modify <N> -a <committer-email> --close FIXED
```

For already-committed tickets: assign + close FIXED. The commit hook auto-adds the hash comment.

### 12. Switch back

```sh
git checkout main
```

## Closing superseded tickets

If the port was already updated and the ticket is stale:
- Comment with `ports <commit-hash>` format (auto-links to FreeBSD cgit)
- Thank the submitter and note the update was already applied
