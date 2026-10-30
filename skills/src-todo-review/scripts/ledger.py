#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
"""Keep the review ledger: one line per marker comment ever seen.

    ledger.py update -l ledger.jsonl -i inventory.jsonl --date YYYY-MM-DD
    ledger.py merge  -l ledger.jsonl -k screen|triage|verify -r results.jsonl --date D
    ledger.py stats  -l ledger.jsonl

"update" adds the items of a new inventory (status "new"), refreshes the
location of known ones, and marks ids that disappeared as "gone" (fixed
upstream, by our commit, or the comment was edited and got a new id).
"merge" records screening, triage or verification results.  The ledger is
the state carried from one weekly run to the next; everything else is
regenerated.

Status values, in the order an item moves through them:
  new        found, not screened yet
  screened   has a screening label
  triaged    has a triage verdict
  verified   a second reviewer agreed with a REMOVE/REWORD/FIX verdict
  disputed   the second reviewer disagreed; needs a human
  committed  the change is in a commit on the review branch
  gone       no longer in the tree
"""

import argparse
import json
import re
import sys
from collections import Counter

KEEP_FROM_INVENTORY = ("path", "line", "start", "end", "markers", "area",
                       "class", "func", "generated", "doctext", "blame_sha",
                       "blame_date", "blame_author", "age", "score")


def load(fn):
    out = {}
    try:
        with open(fn) as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    out[rec["id"]] = rec
    except FileNotFoundError:
        pass
    return out


def save(fn, ledger):
    with open(fn, "w") as f:
        for rec in sorted(ledger.values(), key=lambda r: (r["path"], r["line"], r["id"])):
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def update(args, ledger):
    seen = set()
    for line in open(args.inventory):
        if not line.strip():
            continue
        it = json.loads(line)
        seen.add(it["id"])
        rec = ledger.get(it["id"])
        if rec is None:
            rec = ledger[it["id"]] = {"id": it["id"], "status": "new",
                                      "first_seen": args.date,
                                      "comment": it["comment"][:500]}
        elif rec["status"] == "gone":
            rec["status"] = rec.get("status_before_gone", "new")
        for k in KEEP_FROM_INVENTORY:
            if k in it:
                rec[k] = it[k]
        rec["last_seen"] = args.date
        rec["head"] = it["head"]
    for rec in ledger.values():
        if rec["id"] not in seen and rec["status"] != "gone":
            rec["status_before_gone"] = rec["status"]
            rec["status"] = "gone"
            rec["gone_date"] = args.date


def as_range(v):
    """Agents write [first, last], "first-last" or "first,last"."""
    if isinstance(v, str):
        a, b = re.split(r"[-,:\s]+", v.strip())[:2]
        return [int(a), int(b)]
    return [int(v[0]), int(v[1])] if v else v


def merge(args, ledger):
    for line in open(args.results):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("range") is not None:
            r["range"] = as_range(r["range"])
        rec = ledger.get(r["id"])
        if rec is None:
            print("unknown id %s" % r["id"], file=sys.stderr)
            continue
        if args.kind == "screen":
            rec.update({"screen_label": r["label"], "screen_prio": r["prio"],
                        "screen_why": r.get("why", ""), "screen_date": args.date})
            if rec["status"] == "new":
                rec["status"] = "screened"
        elif args.kind == "triage":
            for k in ("verdict", "confidence", "summary_zh", "rationale",
                      "evidence", "range", "replacement", "fix", "effort",
                      "risk", "patch"):
                if k in r:
                    rec[k] = r[k]
                else:
                    rec.pop(k, None)
            rec["triage_date"] = args.date
            rec["triage_head"] = rec.get("head")
            if rec["status"] in ("new", "screened"):
                rec["status"] = "triaged"
        elif args.kind == "accept":
            # A human (or the orchestrator, reading the diff) accepts the
            # second reviewer's corrected text for a disputed item.
            rec["status"] = "verified"
            rec["accepted_by"] = r.get("by", "orchestrator")
            rec["accept_note"] = r.get("note", "")
        elif args.kind == "verify":
            rec["verify_agree"] = r["agree"]
            rec["verify_verdict"] = r["verdict"]
            rec["verify_notes"] = r.get("notes", "")
            if "replacement" in r:
                rec["verify_range"] = r.get("range")
                rec["verify_replacement"] = r["replacement"]
            rec["verify_date"] = args.date
            if rec["status"] == "triaged":
                rec["status"] = "verified" if r["agree"] else "disputed"


def stats(args, ledger):
    c = Counter(r["status"] for r in ledger.values())
    print("status:", dict(c))
    c = Counter(r.get("screen_label", "-") for r in ledger.values() if r["status"] != "gone")
    print("screen:", dict(c))
    c = Counter(r.get("verdict", "-") for r in ledger.values() if r["status"] != "gone")
    print("verdict:", dict(c))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["update", "merge", "stats"])
    ap.add_argument("-l", dest="ledger", required=True)
    ap.add_argument("-i", dest="inventory")
    ap.add_argument("-k", dest="kind", choices=["screen", "triage", "verify", "accept"])
    ap.add_argument("-r", dest="results")
    ap.add_argument("--date")
    args = ap.parse_args()
    ledger = load(args.ledger)
    if args.cmd == "update":
        update(args, ledger)
    elif args.cmd == "merge":
        merge(args, ledger)
    else:
        stats(args, ledger)
        return
    save(args.ledger, ledger)


if __name__ == "__main__":
    main()
