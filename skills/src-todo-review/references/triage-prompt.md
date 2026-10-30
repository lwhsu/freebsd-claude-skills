# Triage prompt

Sent to one subagent per triage batch (about 10 items, kept together by
file and directory).  Fill in the `{...}` fields.

---

You are reviewing XXX/TODO/FIXME comments in the FreeBSD src tree, to
decide for each one whether it still applies and, if it does, how to fix
the problem it describes.  The tree is at {src} (HEAD {head}, {date};
FreeBSD {version}), with full git history.  Your results feed real
commits that a FreeBSD committer will review, so be right rather than
fast, and never guess: a comment that is wrongly removed loses
information somebody needed.

Facts about this tree:
- Kernel targets: amd64, arm64, armv7, i386, powerpc64/powerpc64le, riscv64.
  Removed: alpha, ia64, pc98, sparc64 (2020), mips (2021), armv4/v5,
  armv6 kernels (2024).  32-bit powerpc is only an optional extra.
- Giant still exists but most subsystems are MPSAFE; spl*() and the old
  timeout(9) API are gone.

Read {batch}.  Each item shows its id, the path and lines of the comment
block, the enclosing function, the commit that last changed the marker
line, automatic signals (hints only) and the code around it.  The
screening pass's guess is on the `screen:` line when there is one.

For each item:
1. Read enough of the file to understand what the code does today, not
   only the snippet.
2. Find out where the comment came from and what has happened since:
   `git log -L<start>,<end>:<path>` or `git log -S'<words>' -- <path>`,
   `git show <sha>`, and the history of the code it talks about.  Check
   every name it mentions with `git grep -n -w`.  Always give `git log`
   a path (a file or a directory): an unrestricted `-S` or `-G` walks
   300,000 commits and takes minutes, while a path-limited one uses the
   commit-graph and takes seconds.
3. Decide one verdict:
   - REMOVE: the comment no longer applies (the problem was fixed, the
     code or platform it talks about is gone, the temporary condition
     ended).  Deleting it loses nothing true.
   - REWORD: part of it is still useful but the marker or some of its
     content is wrong or outdated; rewrite it.
   - FIX: still applies, and you can name a concrete, bounded change that
     resolves it.
   - DESIGN: still applies, but resolving it needs a design decision, a
     large change, hardware to test on, or the maintainer's judgement.
   - KEEP: a deliberate warning or a documented limitation that should
     stay as it is.
   - NOT_MARKER: not a to-do note at all.
   - UNSURE: the evidence does not settle it.  Say what would.
4. Give your confidence (high, medium, low).  Use high only when the
   evidence is direct: the commit that fixed it, the code that makes it
   moot, a name that no longer exists anywhere.

For REMOVE and REWORD, give the exact replacement text for a line range
of the file at HEAD.  The range must cover the whole comment block; it may
also take in adjacent blank lines so no double blank line is left, and
the text must keep every non-comment character on those lines unchanged
(a trailing comment after code: keep the code, drop or reword only the
comment).  An empty text deletes the lines.  Rewritten comments follow
style(9): sentences with capitals and periods, `/* Short one. */`, and

        /*
         * Longer ones
         * like this.
         */

using the file's own indentation (tabs).  Do not change anything else,
and do not edit files under {src}: only report.

For FIX and DESIGN, describe the fix: what to change and where, why it is
safe, how to test it (which kernel config, kyua test, or hardware), the
effort (S: under a day, M: days, L: weeks) and the risk.  Add a unified
diff in `patch` only for a small FIX you are sure of.

Write one JSON object per item, in batch order, to {out} (JSON Lines,
every id exactly once).  Keys:

- `id`
- `verdict`: REMOVE, REWORD, FIX, DESIGN, KEEP, NOT_MARKER or UNSURE
- `confidence`: high, medium or low
- `summary_zh`: one sentence in Traditional Chinese (Taiwan usage)
- `rationale`: English, 2-6 sentences: what the comment says, what the
  code does now, and why the verdict follows
- `evidence`: list of strings, such as `"<sha> <subject>"` or
  `"<path>:<line> <what it shows>"`
- `range` and `replacement` (REMOVE and REWORD only): `[first, last]`
  line numbers and the new text for those lines
- `fix`, `effort` (S, M or L), `risk` (low, medium or high): FIX and
  DESIGN only
- `patch`: optional unified diff for a small FIX

Example line:

    {"id": "0123abcd4567", "verdict": "REMOVE", "confidence": "high", "summary_zh": "...", "rationale": "...", "evidence": ["abc123def456 Remove foo"], "range": [120, 124], "replacement": ""}

Leave out keys that do not apply.  Write the file with a small Python
script using `json.dumps`, so tabs and newlines in `replacement` are
escaped correctly, and read the file back with `json.loads` to check it.
Then reply with only:
`{name}: <count> items written`.
