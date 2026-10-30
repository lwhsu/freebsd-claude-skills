# Lessons from past runs

Read this before starting a run.  Add to it at the end of every run: what
was slow or wrong, and what the next run does instead.  When a lesson can
be enforced by a script or a prompt, change that and note it here.

## 2026-10-29 (first run)

- The cloud checkout was shallow (99 commits).  `git fetch --unshallow
  freebsd main` took 7 minutes and 3 GB; blame is useless without it.
- `git commit-graph write --reachable --changed-paths` (30 seconds) made
  `git blame` four times faster (3.1 s to 0.8 s per line on a 30-year-old
  file).  Blame of 3,691 files still takes about 25 minutes on 4 CPUs.
- `git grep -F -f` with 2,600 identifiers ran for minutes; ripgrep does
  the same in 5 seconds.  `signals.py` uses `rg` when it is installed.
- An unrestricted `git log -S` walks all 314,000 commits: minutes of CPU
  and 2 GB of RSS each, and 16 agents running them at once stalled the
  machine.  The prompts now forbid `-S`/`-G` in screening and require a
  path for them in triage and verification.
- The Workflow tool runs at most min(16, CPUs - 2) agents at once, which
  is 2 on a 4-CPU container.  Background agents started with the Agent
  tool, 16 at a time, were the practical way to fan out.
- Agents write their results to a file and reply with one line, so 160
  completions cost the orchestrator a few hundred tokens each.
- Screening cost about 165k subagent tokens and 8 minutes per batch of
  100 items.
- Lexer fixes found by reading `misses.txt`: `Makefile.inc` must be read
  as make, not C; the ath HAL `.ini` files are C; `share/i18n` `.src`
  files use `#`; a bare `XXX` line inside `#if 0` is a note.
- LinuxKPI marks unimplemented functions with a `TODO()` macro and
  `pr_debug("TODO")`; about 300 of the 617 markers outside comments.  They
  are not comments and are left out, but they are a list of missing
  LinuxKPI functions if anyone wants one.
- Identical comments in one file (`XXX TBD` appears hundreds of times in
  the `sys/cam/scsi/scsi_all.c` sense tables) each became an item.  The
  screening agent handled them quickly and correctly, but they should be
  one cluster: screen and triage it once, apply the verdict to all.
- The Agent tool allows 20 concurrent subagents
  (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`); a launch beyond that is
  refused.  Keep 19 screening agents and one slot for other work, and
  start the next batch as each one reports back.
- The container restarted in the middle of the triage wave and stopped
  all 20 running agents.  Files under the scratchpad and the checkouts
  survived.  Resuming each stopped agent with SendMessage to its agent
  id let it continue from its transcript; `collect.py` then tells which
  batches still lack output, and those are simply run again.  Keep every
  agent's output in a file named after its batch so that a restart costs
  nothing but time.
- Deep triage is the expensive step: about 23 minutes, 100 tool calls and
  250k subagent tokens per batch of 10.  The pilot batch found three real
  bugs (two memory errors and a locking error) and its verifier
  reproduced the first one independently, so the depth pays off; size the
  weekly `-n` to the token budget rather than shrinking the per-item
  effort.
- Verification (52 agents, 551 claims) disputed 10 claims, 1.8%, and
  each dispute was real: a rewording that misdescribed the code, a
  patch that changed the wrong field, a removal of a note that still
  held.  In 4 of the 10 the second reviewer agreed with the verdict and
  only corrected the text; after checking the corrected text against
  the code, the orchestrator accepted those with `ledger.py merge -k
  accept`.  Do not skip the second review to save tokens: it is what
  catches confident mistakes.
- `claims.py` queues only claims it has not queued before, so
  verification started while triage was still running and the two
  waves overlapped by about an hour.
- Agents wrote line ranges as `[47, 49]`, `"47-49"` and `"47,49"`;
  `ledger.py` now accepts all three.  Keep the prompts strict and the
  merge lenient.
- `apply.py` rejected three edits in manual pages: deleting a whole
  `.\"` line removed a `.` that the token comparison counted.  A line
  that holds only a roff comment is now skipped by the comparison.
- 551 of 575 triaged items (96%) needed a change and only one was KEEP:
  the priority-1 screening labels pick the right items.  Priority-2
  items (about 1,300 outside vendor code) are likely to have more KEEP
  and DESIGN verdicts.
- `inventory.py` took `sys/conf/options` for a generated file because
  its header mentions "LINT (generated from NOTES)"; the pattern now
  ignores "generated from" right after "(".  Comments in really
  generated files (OpenSSL manual pages built from pod, flex output, a
  configure header, SWIG output: 23 this run) are never screened, by
  design.
- Writing 37 commit messages in the orchestrator would have filled its
  context with briefs and diffs.  Seven writer agents, five or six
  groups each (`references/commit-prompt.md`), took 9 to 10 minutes and
  about 200k tokens each; every hash they cited resolved, and reading
  all the messages took the orchestrator a quarter of an hour.
- The FIX verdicts came with 184 patches that all apply to HEAD.  They
  change code that nobody has built or run, so they are exported per
  component (`fixes.py`) for a person to take up, never committed.
  Export them before the comment edits are applied, so `git apply
  --check` runs against the tree the reviewers saw.
- `git stash` around a script that must see the pristine tree is fine
  while agents only read: they were told not to touch the src tree.
- A `__pycache__/*.pyc` got committed to the skills repo; the repo now
  ignores `__pycache__/`.
- Total subagent cost of the first run: about 49M tokens (screening
  21.6M, triage 16.2M, verification 11.5M) plus commit messages and the
  fix sorting, in about five hours of wall time.
- Several FIX verdicts are unpatched vulnerabilities that a remote peer,
  a guest or a jail can trigger.  The first plan kept the ledger and the
  patches in this repo, which is public, and would have published them.
  The state now lives in a private place, the fix sorting agent flags
  `secteam` items, and those go to secteam@FreeBSD.org before anything
  else.  Keep vulnerability details out of this repo, lessons included.
