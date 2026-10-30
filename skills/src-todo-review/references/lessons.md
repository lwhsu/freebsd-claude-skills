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
