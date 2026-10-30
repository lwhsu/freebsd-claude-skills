#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
"""Write verification batches: the REMOVE, REWORD and FIX verdicts that a
second reviewer has not checked yet.

    claims.py -C srcdir -l ledger.jsonl -o outdir [-n 12]

Each batch file shows, per item, the verdict with its rationale and
evidence, the proposed edit as a diff against the file at HEAD, the fix
proposal, and the code around the comment.  outdir/manifest.json lists
the batches like batches.py does; a later call adds batches for the claims
that are not in it yet, so verification can start while triage runs.
"""

import argparse
import json
import os
from collections import OrderedDict

CONTEXT = 8


def render(src, r):
    try:
        with open(os.path.join(src, r["path"]), encoding="utf-8",
                  errors="replace") as f:
            lines = f.read().split("\n")
    except OSError:
        lines = []
    out = ["### %s  %s:%d-%d" % (r["id"], r["path"], r["start"], r["end"]),
           "verdict: %s (confidence %s)" % (r["verdict"], r.get("confidence", "?")),
           "rationale: %s" % r.get("rationale", "")]
    if r.get("evidence"):
        out.append("evidence:")
        out += ["- %s" % e for e in r["evidence"]]
    if r["verdict"] in ("REMOVE", "REWORD") and r.get("range"):
        s, e = r["range"]
        out.append("proposed edit of lines %d-%d:" % (s, e))
        out.append("```diff")
        out += ["-%s" % l for l in lines[s - 1:e]]
        rep = r.get("replacement", "")
        if rep:
            out += ["+%s" % l for l in rep.rstrip("\n").split("\n")]
        out.append("```")
    if r.get("fix"):
        out.append("fix (effort %s, risk %s): %s" % (r.get("effort", "?"),
                                                     r.get("risk", "?"), r["fix"]))
    if r.get("patch"):
        out += ["patch:", "```diff", r["patch"].rstrip("\n"), "```"]
    lo = max(1, r["start"] - CONTEXT)
    hi = min(len(lines), r["end"] + CONTEXT)
    out.append("code at HEAD, lines %d-%d:" % (lo, hi))
    out.append("```")
    out += ["%6d| %s" % (n, lines[n - 1].rstrip()[:200]) for n in range(lo, hi + 1)]
    out.append("```")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-C", dest="src", default=".")
    ap.add_argument("-l", dest="ledger", required=True)
    ap.add_argument("-o", dest="out", required=True)
    ap.add_argument("-n", dest="size", type=int, default=12)
    ap.add_argument("--prefix", default="verify")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    mfile = os.path.join(args.out, "manifest.json")
    manifest = []
    if os.path.exists(mfile):
        # Claims already queued in an earlier call are not queued again.
        with open(mfile) as f:
            manifest = json.load(f)
    queued = {i for m in manifest for i in m["ids"]}
    recs = [json.loads(l) for l in open(args.ledger) if l.strip()]
    todo = [r for r in recs if r.get("status") == "triaged"
            and r.get("verdict") in ("REMOVE", "REWORD", "FIX")
            and r["id"] not in queued]
    groups = OrderedDict()
    for r in sorted(todo, key=lambda r: (r["area"], r["path"], r["line"])):
        groups.setdefault(r["area"], []).append(r)
    batches, cur = [], []
    for area, rs in groups.items():
        for r in rs:
            if len(cur) >= args.size:
                batches.append(cur)
                cur = []
            cur.append(r)
    if cur:
        batches.append(cur)

    for n, b in enumerate(batches, len(manifest) + 1):
        name = "%s-%03d" % (args.prefix, n)
        fn = os.path.join(args.out, name + ".md")
        with open(fn, "w") as f:
            f.write("# %s: %d claims\n\n" % (name, len(b)))
            for r in b:
                f.write(render(args.src, r) + "\n")
        manifest.append({"batch": name, "file": fn, "n": len(b),
                         "areas": sorted(set(r["area"] for r in b)),
                         "ids": [r["id"] for r in b]})
    with open(mfile, "w") as f:
        json.dump(manifest, f, indent=1)
    print("%d claims in %d batches" % (len(todo), len(batches)))


if __name__ == "__main__":
    main()
