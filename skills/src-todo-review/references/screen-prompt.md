# Screening prompt

Sent to one subagent per screening batch (about 100 items).  Fill in the
`{...}` fields.  The subagent writes JSON Lines to `{out}` and replies with a
single line, so the orchestrator's context stays small.

---

You are screening XXX/TODO/FIXME comments in the FreeBSD src tree to decide
which ones deserve a closer look.  The tree is checked out at {src} (HEAD
{head}, {date}; FreeBSD {version}).  Full git history is available.

Facts about this tree:
- Kernel targets: amd64, arm64, armv7, i386, powerpc64/powerpc64le, riscv64.
  Removed: alpha, ia64, pc98, sparc64 (2020), mips (2021), armv4/v5,
  armv6 kernels (2024).  32-bit powerpc is only an optional extra.
- Giant still exists but most subsystems are MPSAFE; spl*() and the old
  timeout(9) API are gone.

Read {batch}.  Each item shows its id, the path and lines of the comment
block, the markers, the enclosing function, the commit that last changed
the marker line, automatic signals, and the code around it (">>" marks the
marker line).  Signals are hints, not proof: `missing_ids` lists names in
the comment that occur nowhere else in the tree.

Give every item one label:
- STALE: very likely no longer applies.  The problem looks fixed, the code,
  API, feature or platform it talks about is gone, or a "temporary" / "for
  now" / "remove after X" condition has passed.
- ACTIONABLE: still applies and names a concrete defect or missing piece
  that a bounded change could fix.
- NOTE: still applies but is informational: a known limitation, a
  deliberate trade-off, a hardware quirk, or an open design question with
  no small fix.
- NOT_MARKER: not a to-do note ("XXX" as a placeholder or example, or text
  that only mentions the word).
- LOOK: cannot tell from the snippet; needs an investigation.

Also give `prio`: 1 = review first (likely removable, or an easy and
useful fix), 2 = worth a review, 3 = low value.  And `why`: one short
English sentence naming the concrete reason ("ifq_* removed in 2019",
"i386-only, still supported", "documents a chip erratum").

You may check a hunch with a few read-only commands in {src}
(`git grep -n -w name`, `git log --oneline -3 -- <path>`, `ls`), but keep
it light: about 20 tool calls for the whole batch.  Do not run
`git log -S` or `-G`: over 300,000 commits each one takes minutes.  Most
items are judged from the snippet and your knowledge of FreeBSD.  Do not
modify anything under {src}.

Write the results to {out} as JSON Lines, one line per item in batch order,
every id exactly once:

    {"id": "<id>", "label": "STALE", "prio": 1, "why": "<sentence>"}

Write it with a small Python script using `json.dumps` and read it back
to check that every line parses.  Then reply with only:
`{name}: <count> items written`.
