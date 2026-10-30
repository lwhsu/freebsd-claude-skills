#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
"""Export the proposed fixes as patch files for review, one per component.

    fixes.py -C srcdir -l ledger.jsonl -o outdir [--status verified]

Writes outdir/<component>.patch with every FIX item of that component
that carries a patch: a header (id, location, the reviewers' rationale and
the second review's notes) followed by the diff, so the file reads like a
small patch series.  Each patch is also checked with `git apply --check`
against the tree, and the result goes into outdir/index.tsv.  Nothing is
applied; these are proposals that still need a build and a human.  Run it
before the comment edits are applied, so that the check sees the tree the
reviewers saw.

outdir/items.md lists every open FIX and DESIGN item, patch or not, with
its summary, rationale and fix cut to a few lines each: the input for
references/fix-sort-prompt.md.
"""

import argparse
import json
import os
import subprocess
import sys
import textwrap
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commits import component  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-C", dest="src", default=".")
    ap.add_argument("-l", dest="ledger", required=True)
    ap.add_argument("-o", dest="out", required=True)
    ap.add_argument("--status", nargs="*", default=["verified"])
    args = ap.parse_args()

    recs = [json.loads(l) for l in open(args.ledger) if l.strip()]
    fixes = [r for r in recs if r.get("verdict") == "FIX" and r.get("patch")
             and r["status"] in args.status]
    groups = OrderedDict()
    for r in sorted(fixes, key=lambda r: (component(r["path"]), r["path"], r["line"])):
        groups.setdefault(component(r["path"]), []).append(r)
    os.makedirs(args.out, exist_ok=True)
    index = ["id\tcomponent\tpath\tline\tstatus\tapplies\teffort\trisk"]
    for name, rs in groups.items():
        with open(os.path.join(args.out, name + ".patch"), "w") as f:
            for r in rs:
                patch = r["patch"].rstrip("\n") + "\n"
                chk = subprocess.run(["git", "-C", args.src, "apply", "--check", "-"],
                                     input=patch, text=True, capture_output=True)
                ok = "yes" if chk.returncode == 0 else "no"
                f.write("From: %s %s:%d (%s, applies: %s)\n" % (r["id"], r["path"], r["line"],
                                                                 r["status"], ok))
                f.write("Subject: %s\n\n" % r.get("summary_zh", ""))
                for para in (r.get("rationale", ""), r.get("fix", "")):
                    if para:
                        f.write(textwrap.fill(para, 72) + "\n\n")
                if r.get("verify_notes"):
                    f.write(textwrap.fill("Second review: " + r["verify_notes"], 72) + "\n\n")
                f.write("---\n" + patch + "\n")
                index.append("\t".join([r["id"], name, r["path"], str(r["line"]),
                                        r["status"], ok, r.get("effort", ""),
                                        r.get("risk", "")]))
    with open(os.path.join(args.out, "index.tsv"), "w") as f:
        f.write("\n".join(index) + "\n")
    print("%d fixes in %d files" % (len(fixes), len(groups)))

    todo = [r for r in recs if r.get("verdict") in ("FIX", "DESIGN")
            and r["status"] in ("triaged", "verified", "disputed")]
    todo.sort(key=lambda r: (r["verdict"], r["path"], r["line"]))
    with open(os.path.join(args.out, "items.md"), "w") as f:
        f.write("# FIX and DESIGN items: %d\n\n" % len(todo))
        for r in todo:
            f.write("## %s %s %s:%d status=%s effort=%s risk=%s\n" % (
                r["id"], r["verdict"], r["path"], r["line"], r["status"],
                r.get("effort", "?"), r.get("risk", "?")))
            for k, v in (("zh", r.get("summary_zh", "")), ("why", r.get("rationale", "")),
                         ("fix", r.get("fix", ""))):
                v = " ".join(v.split())
                f.write("%s: %s\n" % (k, v[:600]))
            f.write("\n")
    print("%d FIX and DESIGN items in items.md" % len(todo))


if __name__ == "__main__":
    main()
