#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
"""Split inventory items into review batches for subagents.

    batches.py -C srcdir -o outdir -n size [--ids idfile] < items.jsonl

Items are kept together by file, then by area, so that one agent reads
related code.  A file with more items than a batch holds is split.  Each
batch is written as outdir/batch-NNN.md (the items with their comment, the
code around it and the signals) and listed in outdir/manifest.json.
Generated files are left out.  With --ids, only the listed ids are used.
"""

import argparse
import json
import os
import sys
from collections import OrderedDict

CONTEXT_BEFORE = 4
CONTEXT_AFTER = 10
MAX_COMMENT_LINES = 30


def snippet(lines, it):
    start, end = it["start"], it["end"]
    lo = max(1, start - CONTEXT_BEFORE)
    hi = min(len(lines), end + CONTEXT_AFTER)
    show = list(range(lo, hi + 1))
    if end - start + 1 > MAX_COMMENT_LINES:
        keep = set(range(lo, start + 8)) | set(range(end - 5, hi + 1))
        for ml in it.get("marker_lines", [it["line"]]):
            keep |= set(range(ml - 4, ml + 5))
        show = [n for n in show if n in keep]
    out = []
    prev = None
    for n in show:
        if prev is not None and n != prev + 1:
            out.append("     | [...]")
        mark = ">>" if n == it["line"] else "  "
        out.append("%s%5d| %s" % (mark, n, lines[n - 1].rstrip()[:200]))
        prev = n
    return "\n".join(out)


def render(src, it, cache):
    path = it["path"]
    if path not in cache:
        try:
            with open(os.path.join(src, path), encoding="utf-8",
                      errors="replace") as f:
                cache.clear()
                cache[path] = f.read().split("\n")
        except OSError:
            cache[path] = []
    lines = cache[path]
    head = ["### %s  %s:%d-%d" % (it["id"], path, it["start"], it["end"])]
    meta = "markers: %s" % ",".join(it["markers"])
    if it.get("func"):
        meta += "  function: %s()" % it["func"]
    meta += "  class: %s" % it["class"]
    if it.get("doctext"):
        meta += "  (manual page text)"
    head.append(meta)
    if it.get("blame_sha"):
        head.append("last changed: %s %s %s \"%s\"" % (
            it["blame_sha"], it.get("blame_date", ""), it.get("blame_author", ""),
            it.get("blame_summary", "")))
    sig = []
    for k in ("timebound", "history", "missing_ids"):
        if it.get(k):
            sig.append("%s=%s" % (k, ",".join(it[k])))
    if sig:
        head.append("signals: " + "  ".join(sig))
    if it.get("screen_label"):
        head.append("screen: %s (prio %s) %s" % (it["screen_label"],
                                                it.get("screen_prio", "?"),
                                                it.get("screen_why", "")))
    body = snippet(lines, it) if lines else "(file not readable)"
    return "\n".join(head) + "\n```\n" + body + "\n```\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-C", dest="src", default=".")
    ap.add_argument("-o", dest="out", required=True)
    ap.add_argument("-n", dest="size", type=int, default=100)
    ap.add_argument("--ids", help="file with one id per line, in order")
    ap.add_argument("--prefix", default="batch")
    ap.add_argument("--fill", type=float, default=0.8,
                    help="start a new batch at an area boundary once the "
                         "current one is this full")
    args = ap.parse_args()

    items = [json.loads(l) for l in sys.stdin if l.strip()]
    items = [it for it in items if not it.get("generated")]
    if args.ids:
        with open(args.ids) as f:
            order = [l.split()[0] for l in f if l.strip()]
        byid = {it["id"]: it for it in items}
        items = [byid[i] for i in order if i in byid]
        # keep files together, in the order of their first selected item
        groups = OrderedDict()
        for it in items:
            groups.setdefault(it["path"], []).append(it)
        groups = OrderedDict((p, sorted(v, key=lambda x: x["line"]))
                             for p, v in groups.items())
    else:
        items.sort(key=lambda it: (it["area"], it["path"], it["line"]))
        groups = OrderedDict()
        for it in items:
            groups.setdefault(it["path"], []).append(it)

    batches, cur, cur_area = [], [], None
    for path, its in groups.items():
        area = its[0]["area"]
        if cur and (len(cur) + len(its) > args.size or
                    (not args.ids and area != cur_area and
                     len(cur) >= args.size * args.fill)):
            batches.append(cur)
            cur = []
        while len(its) > args.size:
            if cur:
                batches.append(cur)
                cur = []
            batches.append(its[:args.size])
            its = its[args.size:]
        cur.extend(its)
        cur_area = area
    if cur:
        batches.append(cur)

    os.makedirs(args.out, exist_ok=True)
    manifest = []
    cache = {}
    for n, b in enumerate(batches, 1):
        name = "%s-%03d" % (args.prefix, n)
        fn = os.path.join(args.out, name + ".md")
        with open(fn, "w") as f:
            f.write("# %s: %d items\n\n" % (name, len(b)))
            for it in b:
                f.write(render(args.src, it, cache) + "\n")
        manifest.append({"batch": name, "file": fn, "n": len(b),
                         "areas": sorted(set(it["area"] for it in b)),
                         "ids": [it["id"] for it in b]})
    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print("%d items in %d batches" % (sum(m["n"] for m in manifest), len(manifest)),
          file=sys.stderr)


if __name__ == "__main__":
    main()
