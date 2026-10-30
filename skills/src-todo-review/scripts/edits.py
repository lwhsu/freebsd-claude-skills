#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
"""List the edits that are ready to apply: verified REMOVE and REWORD
verdicts made on the tree's current HEAD.

    edits.py -l ledger.jsonl --head <sha> > edits.jsonl

The verifier's corrected range and text win over the triage proposal.
Items triaged on an older HEAD are left out (their line numbers may have
moved); triage them again.
"""

import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-l", dest="ledger", required=True)
    ap.add_argument("--head", required=True)
    args = ap.parse_args()

    stale = 0
    for line in open(args.ledger):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("status") != "verified" or r.get("verdict") not in ("REMOVE", "REWORD"):
            continue
        if r.get("triage_head") != args.head:
            stale += 1
            continue
        rng = r.get("verify_range") or r.get("range")
        rep = r["verify_replacement"] if "verify_replacement" in r else r.get("replacement")
        if not rng or rep is None:
            continue
        print(json.dumps({"id": r["id"], "path": r["path"], "range": rng,
                          "replacement": rep, "verdict": r["verdict"],
                          "area": r["area"], "doctext": r.get("doctext", False)},
                         ensure_ascii=False))
    if stale:
        print("%d verified items were triaged on another HEAD; triage again" % stale,
              file=sys.stderr)


if __name__ == "__main__":
    main()
