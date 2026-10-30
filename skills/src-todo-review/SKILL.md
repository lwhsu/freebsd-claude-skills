---
description: "Review the XXX/TODO/FIXME/HACK comments in the FreeBSD src tree: inventory them, screen every one with subagents, triage and cross-verify a batch in depth, commit the comments that are verifiably obsolete, and keep a ledger and a tracking spreadsheet across weekly runs. This skill should be used when the user asks to audit, clean up or track to-do markers in FreeBSD src, or for the weekly run of that review."
user_invocable: true
arguments: "[-n triage-count] [path ...]"
---

# FreeBSD src marker review

Find the `XXX`, `TODO`, `FIXME`, `HACK` and `KLUDGE` notes in the comments
of a FreeBSD src checkout, decide which are obsolete and which still
describe real work, propose fixes, and commit the removals that a second
reviewer agrees with.  One run takes a few hours and is meant to be
repeated weekly: the ledger remembers what was already reviewed, so each
run screens only new comments and triages the next batch of the backlog.

All verdicts are made by subagents.  Nothing goes upstream without a
human: FreeBSD's CONTRIBUTING.md refuses AI-generated changes that have
not had substantial human review.

## Invocation

```
/src-todo-review [-n 300] [path ...]
```

- `-n` — how many items to triage in depth this run (default 300).
- `path` — limit the run to these pathspecs (default: the whole tree).

## Layout

- `$SKILL` — this directory: `scripts/`, `references/`.
- `$SRC` — the src checkout; the upstream remote is `freebsd`.
- `$STATE` — the ledger, carried between runs:
  `data/src-todo-review/ledger.jsonl` at the top of the skills repo.
- `$RUN` — scratch space for this run (batches, agent output); never
  committed.

Every script prints its usage with `-h`.

## Step 0 — Prepare the tree

```sh
git -C $SRC fetch freebsd main
git -C $SRC rev-parse --is-shallow-repository   # must be false
git -C $SRC switch -C <review branch> freebsd/main   # or rebase it
git -C $SRC commit-graph write --reachable --changed-paths
```

A shallow clone breaks blame: `git fetch --unshallow freebsd main` once
(about 7 minutes, 3 GB).  The commit-graph makes blame four times faster.
Note `HEAD`, its date, and the version from `sys/conf/newvers.sh`.

## Step 1 — Inventory

```sh
python3 $SKILL/scripts/inventory.py -C $SRC -m $RUN/misses.txt > $RUN/inventory.jsonl
python3 $SKILL/scripts/blame.py -C $SRC < $RUN/inventory.jsonl > $RUN/blamed.jsonl
python3 $SKILL/scripts/signals.py -C $SRC < $RUN/blamed.jsonl > $RUN/items.jsonl
python3 $SKILL/scripts/ledger.py update -l $STATE/ledger.jsonl -i $RUN/items.jsonl --date <today>
```

`inventory.py` takes 15 seconds; `blame.py` about 25 minutes on 4 CPUs
(run it in the background); `signals.py` seconds with ripgrep installed.
Skim `misses.txt` (markers outside comments): a real comment there means
the lexer in `inventory.py` needs a fix.  `scripts/paths.conf` lists the
vendor directories that are never scanned and the vendor-maintained code
that is triaged last.

`ledger.py update` marks new comments `new` and vanished ones `gone`.
Before going on, look at what went `gone` since the last run and check
it against the commits of the review branch (see Step 7).

## Step 2 — Screen every new item

```sh
jq -r 'select(.status=="new") | .id' $STATE/ledger.jsonl > $RUN/new.ids
python3 $SKILL/scripts/batches.py -C $SRC -o $RUN/screen -n 110 --prefix screen \
    --ids $RUN/new.ids < $RUN/items.jsonl
```

Fill `references/screen-prompt.md` into `$RUN/screen/INSTRUCTIONS.md`
(tree path, HEAD, date, version) and start one subagent per batch, about
16 at a time, in the background.  Each task prompt only names the
instructions file, the batch file and the output file
`$RUN/screen-out/<batch>.jsonl`; the agent replies with one line, which
keeps the orchestrator's context small.  When all are done:

```sh
python3 $SKILL/scripts/collect.py -m $RUN/screen/manifest.json -d $RUN/screen-out \
    -k screen > $RUN/screen.jsonl
python3 $SKILL/scripts/ledger.py merge -l $STATE/ledger.jsonl -k screen -r $RUN/screen.jsonl --date <today>
```

`collect.py` names every incomplete batch; run those again.

## Step 3 — Pick and triage

Select up to `-n` items, in this order, skipping vendor and generated
code until nothing else is left:

1. STALE, prio 1
2. ACTIONABLE, prio 1
3. STALE, prio 2
4. LOOK, prio 1
5. ACTIONABLE, prio 2, then the rest by `score`

```sh
python3 $SKILL/scripts/select.py -l $STATE/ledger.jsonl -n 300 > $RUN/triage.ids
python3 $SKILL/scripts/batches.py -C $SRC -o $RUN/triage -n 10 --prefix triage \
    --ids $RUN/triage.ids < $RUN/items.ledger.jsonl
```

(`select.py` also writes `items.ledger.jsonl`: the items with their
screening labels, so the batch shows them.)  Fill
`references/triage-prompt.md` and start one subagent per batch of about
10 items.  Collect with `-k triage` and merge into the ledger.

## Step 4 — Verify

Every REMOVE, REWORD and FIX verdict goes to a second subagent that did not
make it, with `references/verify-prompt.md`:

```sh
python3 $SKILL/scripts/claims.py -l $STATE/ledger.jsonl -o $RUN/verify -n 12
```

Collect with `-k verify` and merge.  Agreement moves an item to
`verified`; disagreement to `disputed`, which only a human resolves.

## Step 5 — Apply and commit

```sh
python3 $SKILL/scripts/edits.py -l $STATE/ledger.jsonl > $RUN/edits.jsonl
python3 $SKILL/scripts/apply.py -C $SRC < $RUN/edits.jsonl
```

`edits.py` takes the verified REMOVE/REWORD items whose verdict was made
on the current HEAD (re-triage the others), using the verifier's
corrected text when there is one.  `apply.py` refuses any edit that
changes a non-comment token; read every skipped line.  Then read the whole
`git diff` yourself, and commit by subsystem, one commit per area, in the
src commit style:

```
<area>: Remove obsolete XXX comments

<one paragraph per comment or group: what it said and the commit or
fact that made it obsolete>
```

Comment-only changes cannot break the build, but `apply.py` is the proof;
any FIX that changes code needs a build (`tools/cross-buildkernel.sh` from
freebsd-claude-code-cloud for the kernel) and stays out of the comment
commits.  Record the commits in `$STATE/commits.jsonl`
(`{"sha", "subject", "ids", "files"}`), mark their items `committed`, and
push the review branch to the fork (`origin`), never to `freebsd`.

## Step 6 — Report

```sh
python3 $SKILL/scripts/report.py -l $STATE/ledger.jsonl -c $STATE/commits.jsonl \
    -o $RUN/src-todo-review-<date>.xlsx --date <today>
python3 <xlsx skill>/scripts/recalc.py $RUN/src-todo-review-<date>.xlsx 120
```

Recalc must report `"status": "success"` with no errors.  Send the file to
the user.  In the review doc (Claude Docs), add a tab for the run: what
was screened, the triage results, the commits, open questions; update the
summary tab's numbers.  Write findings in the doc, not in chat.

## Step 7 — Keep the process improving

Append to `references/lessons.md` what went wrong or was slow in this run
and how the next run avoids it, and change the scripts or prompts when
the fix is mechanical.  Commit `$STATE` and any skill changes to the
skills repo.  At the start of the next run, read `references/lessons.md`
first.
