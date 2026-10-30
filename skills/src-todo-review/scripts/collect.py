#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
"""Check and merge the JSON Lines that subagents wrote for a set of batches.

    collect.py -m manifest.json -d outdir -k screen|triage|verify > merged.jsonl

Reports, on stderr, every batch whose output is missing or incomplete, and
every line that does not parse or has an invalid value, so those batches
can be run again.  Exits 1 if anything is missing.
"""

import argparse
import json
import os
import sys

VALID = {
    "screen": {"label": {"STALE", "ACTIONABLE", "NOTE", "NOT_MARKER", "LOOK"},
               "prio": {1, 2, 3}},
    "triage": {"verdict": {"REMOVE", "REWORD", "FIX", "DESIGN", "KEEP",
                           "NOT_MARKER", "UNSURE"},
               "confidence": {"high", "medium", "low"}},
    "verify": {"agree": {True, False},
               "verdict": {"REMOVE", "REWORD", "FIX", "DESIGN", "KEEP",
                           "NOT_MARKER", "UNSURE"}},
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-m", dest="manifest", required=True)
    ap.add_argument("-d", dest="outdir", required=True)
    ap.add_argument("-k", dest="kind", required=True, choices=sorted(VALID))
    args = ap.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)
    rules = VALID[args.kind]
    bad = []
    for m in manifest:
        fn = os.path.join(args.outdir, m["batch"] + ".jsonl")
        got = {}
        if os.path.exists(fn):
            with open(fn) as f:
                for n, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        print("%s:%d: does not parse" % (fn, n), file=sys.stderr)
                        continue
                    errs = [k for k, ok in rules.items() if rec.get(k) not in ok]
                    if errs or rec.get("id") not in m["ids"]:
                        print("%s:%d: bad %s" % (fn, n, ",".join(errs) or "id"),
                              file=sys.stderr)
                        continue
                    rec["batch"] = m["batch"]
                    got[rec["id"]] = rec
        missing = [i for i in m["ids"] if i not in got]
        if missing:
            bad.append(m["batch"])
            print("%s: %d of %d missing" % (m["batch"], len(missing), len(m["ids"])),
                  file=sys.stderr)
        for i in m["ids"]:
            if i in got:
                sys.stdout.write(json.dumps(got[i], ensure_ascii=False) + "\n")
    if bad:
        print("incomplete: %s" % " ".join(bad), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
