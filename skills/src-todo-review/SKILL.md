---
description: "Review the XXX/TODO/FIXME/HACK comments in the FreeBSD src tree: inventory them, screen every one with subagents, triage and cross-verify a batch in depth, commit the comments that are verifiably obsolete, export the proposed fixes as patches, and keep a ledger, a tracking spreadsheet and a review doc across weekly runs. This skill should be used when the user asks to audit, clean up or track to-do markers in FreeBSD src, or for the weekly run of that review."
user_invocable: true
arguments: "[-n triage-count] [path ...]"
---

# FreeBSD src marker review

Find the `XXX`, `TODO`, `FIXME`, `HACK` and `KLUDGE` notes in the comments
of a FreeBSD src checkout, decide which are obsolete and which still
describe real work, propose fixes, and commit the removals that a second
reviewer agrees with.  A run is meant to be repeated weekly: the ledger
remembers what was already reviewed, so each run screens only new
comments and triages the next part of the backlog.

All verdicts are made by subagents and checked by a second one.  Nothing
goes upstream without a human: FreeBSD's CONTRIBUTING.md refuses
AI-generated changes that have not had substantial human review, so the
commits and patches are proposals for a committer to review.

Read `references/lessons.md` before starting.

## Invocation

```
/src-todo-review [-n 300] [path ...]
```

- `-n` — how many items to triage in depth this run (default 300).
- `path` — limit the run to these pathspecs (default: the whole tree).

## Layout

- `$SKILL` — this directory: `scripts/`, `references/`.
- `$SRC` — the src checkout; the upstream remote is `freebsd`.
- `$STATE` — `data/src-todo-review/` at the top of the skills repo:
  `ledger.jsonl` (every marker comment ever seen and what was decided) and
  `commits.jsonl` (the commits made for it), carried between runs.
- `$RUN` — scratch space for this run (batches, agent output); never
  committed.

Every script prints its usage with `-h`.

## Cost

Measured on the first run (11,926 comments, 4-CPU container):

| Step | Batch | Per batch | Per item |
| --- | --- | --- | --- |
| Screen | ~100 items | 175k tokens, 17 tool calls, 10 min | 1.8k tokens |
| Triage | 10 items | 258k tokens, 89 tool calls, 21 min | 28k tokens |
| Verify | 12 claims | 221k tokens, 98 tool calls, 20 min | 21k tokens |

551 of the 575 items triaged in the first run needed a change (remove,
reword or fix), so verification costs nearly as much as triage: budget
about 50k subagent tokens per triaged item, 15M for `-n 300`.  The Agent tool runs at most 20
subagents at once; keep 19 busy and one slot free, and start the next
batch as each one reports back.  Weekly screening of new comments is one
or two batches.

## Step 0 — Prepare the tree

```sh
git -C $SRC fetch freebsd main
git -C $SRC rev-parse --is-shallow-repository   # must be false
git -C $SRC switch -C <run branch> freebsd/main
git -C $SRC commit-graph write --reachable --changed-paths
```

The run branch starts from `freebsd/main` every week (the session's
designated branch, or `src-todo-review/<date>`).  The inventory then
describes upstream: items committed in earlier runs are still in the tree
and stay `committed` in the ledger instead of coming back as new, and the
line numbers the reviewers see are the ones the edits apply to.

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
Look at what went `gone` since the last run: a `committed` item that is
gone was taken upstream; anything else was fixed or rewritten upstream.

## Step 2 — Screen every new item

```sh
jq -r 'select(.status=="new") | .id' $STATE/ledger.jsonl > $RUN/new.ids
python3 $SKILL/scripts/batches.py -C $SRC -o $RUN/screen -n 110 \
    --ids $RUN/new.ids < $RUN/items.jsonl
```

`batches.py` leaves out generated files.  Fill
`references/screen-prompt.md` into `$RUN/screen/INSTRUCTIONS.md` (tree
path, HEAD, date, version) and start one subagent per batch in the
background.  Each task prompt only names the instructions file, the batch
file and the output file `$RUN/screen-out/<batch>.jsonl`; the agent
replies with one line, which keeps the orchestrator's context small.
When all are done:

```sh
python3 $SKILL/scripts/collect.py -m $RUN/screen/manifest.json -d $RUN/screen-out \
    -k screen > $RUN/screen.jsonl
python3 $SKILL/scripts/ledger.py merge -l $STATE/ledger.jsonl -k screen -r $RUN/screen.jsonl --date <today>
```

`collect.py` names every incomplete batch; run those again.

## Step 3 — Pick and triage

```sh
python3 $SKILL/scripts/select.py -l $STATE/ledger.jsonl -i $RUN/items.jsonl -n 300 \
    -o $RUN/items.ledger.jsonl > $RUN/triage.ids
python3 $SKILL/scripts/batches.py -C $SRC -o $RUN/triage -n 10 --prefix triage \
    --ids $RUN/triage.ids < $RUN/items.ledger.jsonl
```

`select.py` takes ACTIONABLE, STALE, then LOOK items of priority 1, then
the same of priority 2, by signal score, with vendor-maintained and
generated code last; `--only ACTIONABLE:1` and `--areas sys/net80211`
narrow it.  Fill `references/triage-prompt.md` and start one subagent per
batch of 10.  Collect with `-k triage` and merge into the ledger as each
wave finishes.

## Step 4 — Verify

Every REMOVE, REWORD and FIX verdict goes to a second subagent that did not
make it, with `references/verify-prompt.md`:

```sh
python3 $SKILL/scripts/claims.py -C $SRC -l $STATE/ledger.jsonl -o $RUN/verify -n 12
```

`claims.py` adds batches only for claims not queued yet, so call it after
every triage merge and verification runs alongside triage.  Collect with
`-k verify` and merge.  Agreement moves an item to `verified`;
disagreement to `disputed`.

Read every disputed item.  When the second reviewer agreed with the
verdict but corrected the text or the range, and its version is right
against the code, accept it:

```sh
echo '{"id": "<id>", "by": "<who>", "note": "<what was checked>"}' >> $RUN/accept.jsonl
python3 $SKILL/scripts/ledger.py merge -l $STATE/ledger.jsonl -k accept -r $RUN/accept.jsonl --date <today>
```

Leave the rest `disputed` for the maintainers; the report lists them.

## Step 5 — Export the fix proposals

Before any edit touches the tree:

```sh
python3 $SKILL/scripts/fixes.py -C $SRC -l $STATE/ledger.jsonl -o $RUN/fix-proposals \
    --status verified disputed
```

One patch file per component, each fix with its rationale, the second
review's notes and whether it applies.  These change code; they are never
committed by this skill.  Then start one subagent with
`references/fix-sort-prompt.md` on `$RUN/fix-proposals/items.md`: it
gives every FIX and DESIGN item a category and severity, groups the ones
a single change resolves, and checks the top picks against the code, for
the report and the doc.

## Step 6 — Apply the comment edits

```sh
python3 $SKILL/scripts/edits.py -l $STATE/ledger.jsonl --head <HEAD> > $RUN/edits.jsonl
python3 $SKILL/scripts/apply.py -C $SRC -a $RUN/applied.jsonl < $RUN/edits.jsonl > $RUN/apply.log
```

`edits.py` takes the verified REMOVE and REWORD items triaged on this
HEAD, with the second reviewer's corrected text when there is one.
`apply.py` refuses any edit that changes a non-comment token; read every
`skipped` line.  Then read the whole `git diff` yourself and run
`git diff --check`.

## Step 7 — Commit

```sh
python3 $SKILL/scripts/commits.py plan -C $SRC -l $STATE/ledger.jsonl -e $RUN/applied.jsonl \
    -o $RUN/commits
```

`plan` groups the edits by component (small ones pooled by tree) and
writes a brief per group.  Fill `references/commit-prompt.md` into
`$RUN/commits/INSTRUCTIONS.md` and start one subagent per five or six
groups to write the `.msg` files.  Read every message: subject at most 72
characters, the hashes resolve, every claim is in the brief.  Then:

```sh
python3 $SKILL/scripts/commits.py make -C $SRC -o $RUN/commits \
    --trailer "Co-Authored-By: ..." --trailer "Claude-Session: ..."
cat $RUN/commits/commits.jsonl >> $STATE/commits.jsonl
python3 $SKILL/scripts/ledger.py merge -l $STATE/ledger.jsonl -k commit \
    -r $RUN/commits/commits.jsonl --date <today>
git -C $SRC push -u origin <run branch>
```

Use the trailers the session asks for.  Push to the fork (`origin`),
never to `freebsd`.

## Step 8 — Report

```sh
python3 $SKILL/scripts/report.py -l $STATE/ledger.jsonl -c $STATE/commits.jsonl \
    -o $RUN/src-todo-review-<date>.xlsx --date <today>
python3 <xlsx skill>/scripts/recalc.py $RUN/src-todo-review-<date>.xlsx 120
```

Recalc must report `"status": "success"` with no errors.  Send the file to
the user.  In the review doc (Claude Docs), add a tab for the run: what
was screened, the triage results, the commits, the top fix proposals and
open questions; update the summary numbers.  Write findings in the doc,
not in chat.

## Step 9 — Keep the process improving

Append to `references/lessons.md` what went wrong or was slow in this run
and how the next run avoids it, and change the scripts or prompts when
the fix is mechanical.  Commit `$STATE` and any skill changes to the
skills repo and push.
