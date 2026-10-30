#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
"""Add the commit that last touched each marker line to an inventory.

    blame.py [-C srcdir] [-j jobs] < inventory.jsonl > inventory-blamed.jsonl

Needs the full history (not a shallow clone).  Whitespace-only changes and
the revisions in .git-blame-ignore-revs are skipped, and lines moved within
a file are followed (-w -M).  Adds blame_sha, blame_date (author date,
YYYY-MM-DD), blame_author and blame_summary.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor


def blame_file(src, head, path, lines, ignore):
    cmd = ["git", "-C", src, "blame", "--line-porcelain", "-w", "-M"]
    if ignore:
        cmd += ["--ignore-revs-file", ignore]
    for n in sorted(lines):
        cmd += ["-L", "%d,%d" % (n, n)]
    cmd += [head, "--", path]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    out = {}
    if r.returncode != 0:
        return out
    cur = None
    for ln in r.stdout.split("\n"):
        if ln.startswith("\t"):
            if cur:
                out[cur["final"]] = cur
            cur = None
        elif cur is None:
            f = ln.split()
            if len(f) >= 3:
                cur = {"sha": f[0], "final": int(f[2])}
        else:
            key, _, val = ln.partition(" ")
            if key == "author-mail":
                cur["author"] = val.strip("<>")
            elif key == "author-time":
                cur["date"] = time.strftime("%Y-%m-%d", time.gmtime(int(val)))
            elif key == "summary":
                cur["summary"] = val
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-C", dest="src", default=".")
    ap.add_argument("-j", dest="jobs", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()

    items = [json.loads(l) for l in sys.stdin if l.strip()]
    if not items:
        return
    head = items[0]["head"]
    ignore = os.path.join(args.src, ".git-blame-ignore-revs")
    ignore = ignore if os.path.exists(ignore) else None
    byfile = defaultdict(set)
    for it in items:
        byfile[it["path"]].add(it["line"])

    results = {}
    with ThreadPoolExecutor(args.jobs) as pool:
        futs = {path: pool.submit(blame_file, args.src, head, path, lines, ignore)
                for path, lines in byfile.items()}
        for i, (path, fut) in enumerate(futs.items()):
            results[path] = fut.result()
            if i % 200 == 0:
                print("blame: %d/%d files" % (i, len(futs)), file=sys.stderr)

    for it in items:
        b = results.get(it["path"], {}).get(it["line"])
        if b:
            it["blame_sha"] = b["sha"][:12]
            it["blame_date"] = b.get("date", "")
            it["blame_author"] = b.get("author", "")
            it["blame_summary"] = b.get("summary", "")[:120]
        sys.stdout.write(json.dumps(it, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
