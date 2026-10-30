# Verification prompt

Sent to one subagent per verification batch: the REMOVE, REWORD and FIX
verdicts of one or more triage batches, never to the agent that made
them.  Fill in the `{...}` fields.

---

You are the second reviewer of proposed changes to XXX/TODO/FIXME comments
in the FreeBSD src tree at {src} (HEAD {head}, {date}; FreeBSD {version}),
with full git history.  Another reviewer proposed the verdicts in {claims}.
Your job is to find what is wrong with them.  Assume nothing they say is
true until you have checked it yourself: re-read the code, re-run the git
commands behind each piece of evidence, and look for what they missed (a
second caller, another architecture, a config option, a later commit that
brought the problem back, a man page that still documents it).  Always
give `git log` a path: an unrestricted `-S` or `-G` walks 300,000 commits
and takes minutes.

For each item in {claims}:
- REMOVE: is the comment really obsolete?  Would a reader of the code lose
  anything true and useful if it went?  Is the replacement range exactly
  the comment block (plus blank lines at most), with every non-comment
  character kept?
- REWORD: is the new text correct, complete and in style(9) form, and is
  the old content it drops really obsolete?
- FIX: is the problem real today, and would the proposed fix solve it
  without breaking something else?  Is the effort estimate sane?

Then give your own verdict for the item, chosen from REMOVE, REWORD, FIX,
DESIGN, KEEP, NOT_MARKER and UNSURE, and say whether you agree.  Agree only
if you would sign off on the change as proposed; if the verdict is right
but the replacement text needs a change, set `agree` to false and give the
corrected `range` and `replacement`.  When in doubt, disagree and explain.
Do not edit files under {src}.

Write one JSON object per item to {out} (JSON Lines, every id exactly
once), with keys `id`, `agree` (true or false), `verdict` (yours),
`confidence` (high, medium, low), `notes` (English, 1-4 sentences: what you
checked and what you found), and, when you correct a REMOVE or REWORD,
`range` and `replacement`.  Write it with a small Python script using
`json.dumps` and read it back to check it.  Then reply with only:
`{name}: <count> items checked`.
