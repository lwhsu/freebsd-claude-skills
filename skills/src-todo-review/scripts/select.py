#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
"""Pick the next items to triage in depth.

    select.py -l ledger.jsonl -i items.jsonl -n 300 -o items.ledger.jsonl > triage.ids

Takes screened items that have no triage verdict yet, in this order:
STALE prio 1, ACTIONABLE prio 1, STALE prio 2, LOOK prio 1, ACTIONABLE
prio 2, then the rest by signal score.  Vendor-maintained and generated
code comes after everything else.  Writes the run's items, joined with
their screening labels, to the -o file for batches.py.
"""

import argparse
import json
import sys

TIERS = [("STALE", 1), ("ACTIONABLE", 1), ("STALE", 2), ("LOOK", 1),
         ("ACTIONABLE", 2), ("LOOK", 2)]
DONE = {"triaged", "verified", "disputed", "committed", "gone"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-l", dest="ledger", required=True)
    ap.add_argument("-i", dest="items", required=True)
    ap.add_argument("-n", dest="count", type=int, default=300)
    ap.add_argument("-o", dest="out", required=True)
    ap.add_argument("--areas", nargs="*", help="only these areas (prefixes)")
    args = ap.parse_args()

    ledger = {}
    for line in open(args.ledger):
        if line.strip():
            r = json.loads(line)
            ledger[r["id"]] = r
    items = [json.loads(l) for l in open(args.items) if l.strip()]
    with open(args.out, "w") as f:
        for it in items:
            r = ledger.get(it["id"], {})
            for k in ("screen_label", "screen_prio", "screen_why"):
                if k in r:
                    it[k] = r[k]
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    def rank(it):
        late = it["class"] == "vendor" or it.get("generated")
        key = (it.get("screen_label"), it.get("screen_prio"))
        tier = TIERS.index(key) if key in TIERS else len(TIERS)
        return (late, tier, -it.get("score", 0), it["path"], it["line"])

    cand = [it for it in items
            if it.get("screen_label") and it.get("screen_label") != "NOT_MARKER"
            and ledger.get(it["id"], {}).get("status") not in DONE]
    if args.areas:
        cand = [it for it in cand if any(it["area"].startswith(a) for a in args.areas)]
    cand.sort(key=rank)
    for it in cand[:args.count]:
        print(it["id"])
    print("selected %d of %d candidates" % (min(args.count, len(cand)), len(cand)),
          file=sys.stderr)


if __name__ == "__main__":
    main()
