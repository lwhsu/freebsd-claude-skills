# Commit message prompt

Written to `{out}/INSTRUCTIONS.md` next to the briefs of `commits.py plan`.
One subagent writes the messages for five or six groups; its task prompt
only lists the group names (the `base` of each entry in `plan.json`).
Fill in the `{...}` fields.

---

You write FreeBSD src commit messages for comment-only changes that remove
or rewrite obsolete XXX/TODO/FIXME comments.  Each change was proposed by
one reviewer and independently confirmed by a second; the brief for a
group lists every edit with its rationale and evidence, followed by the
diff.

For each group named in your task, read `<group>.md` in this directory and
write the commit message to `<group>.msg` next to it:

- Subject: `<prefix>: <imperative summary>`, at most 72 characters, no
  trailing period.  The prefix is the component the way FreeBSD commit
  subjects name it (`ath`, `net80211`, `libc`, `cam`, `kern`, `loader`,
  `sound`, ...).  For a pooled group (`sys/dev`, `sys`, `lib`, `bin`,
  `usr.sbin`, `misc`) use that as the prefix.  Typical subjects:
  `ath: Remove stale XXX comments`, `net80211: Update outdated comments`.
- A blank line, then the body, wrapped at 72 columns.  Start with one
  sentence saying what kind of comments go and why.  Then one short
  paragraph or `-` item per edit, or per set of identical edits: the file,
  what the comment claimed or asked for, and the fact that settles it,
  citing the commit with 12 hex digits and its subject in quotes when
  there is one (`4f2a1c3b5d6e ("Remove foo")`).  Facts only, taken from
  the brief; if the brief does not say it, do not write it.
- End the body with the line `No functional change.`
- No trailers; they are added later.

Check every hash you cite with `git -C {src} show --no-patch
--format='%h %s' <hash>` and fix or drop any that do not resolve.  Do not
modify the src tree.  When all your messages are written, reply with only:
`<count> messages written`.
