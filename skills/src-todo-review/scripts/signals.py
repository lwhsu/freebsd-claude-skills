#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
"""Add cheap staleness signals to inventory items, for ordering the review.

    signals.py [-C srcdir] < inventory.jsonl > inventory-signals.jsonl

Adds:
  timebound     wording that expires ("for now", "temporary", "remove once")
  history       references to old releases, removed platforms, Giant, spl*()
  missing_ids   identifiers named in the comment that occur nowhere else in
                the tree (only in marker comments): often removed code
  bare          the comment says little beyond the marker itself
  age           years since the blamed commit (needs blame.py output)
  score         a rough ordering key; higher is more likely stale or easy
None of these is a verdict.  They only decide what a reviewer reads first.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter

TIMEBOUND_RE = re.compile(
    r"\b(temporar(?:y|ily)|for now|for the time being|in the meantime|"
    r"until\b|stopgap|short[- ]term|transition(?:al)?|deprecated?|"
    r"obsolete|no longer|not (?:yet )?(?:needed|used)|unused|dead code|"
    r"go(?:es)? away|remove (?:this|it|me|once|when|after)|"
    r"(?:remove|delete|drop|kill)\b.{0,40}\b(?:when|once|after|eventually|someday|soon)|"
    r"(?:when|once) .{0,60}(?:is|are) (?:fixed|done|committed|merged|converted|gone|removed))",
    re.I)
HISTORY_RE = re.compile(
    r"\b(FreeBSD ?[1-9][0-9]?(?:\.[0-9x])?\b|[1-9][0-9]?\.[0-9x]-(?:RELEASE|STABLE|CURRENT)|"
    r"RELENG_|__FreeBSD_version|\bcvs\b|\bsvn\b|\br[1-9][0-9]{4,5}\b|"
    r"\bGiant\b|\bspl(?:net|bio|tty|imp|high|clock|vm|x|soft|0)\b|NEEDSGIANT|"
    r"D_NEEDGIANT|\b(?:ia64|sparc64|pc98|alpha|mips(?:64)?|armv[456]|armeb|"
    r"powerpcspe|sun4v|xscale|ISA bus|EISA|MCA)\b|\begcs\b|\bgcc ?[234]\b|"
    r"\bK&R\b|\blint\b|COMPAT_43\b|COMPAT_FREEBSD[0-9]+|4\.4 ?BSD|Lite2?\b|"
    r"\bold[- ]style\b|\bpre-?(?:newbus|SMPng|VFS|MPSAFE))", re.I)
FUNC_REF_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\(\)")
SNAKE_RE = re.compile(r"\b([a-z][a-z0-9]*_[a-z0-9_]*[a-z0-9])\b")
MACRO_RE = re.compile(r"\b([A-Z][A-Z0-9]*_[A-Z0-9_]*[A-Z0-9])\b")
MARKERS_RE = re.compile(r"(?<![A-Za-z0-9_])(XXXX?|TODO|FIXME|HACK|KLUDGE)[:!?.]*")


def strip_markers(text):
    return MARKERS_RE.sub("", " ".join(text.split())).strip()


def ids_in(text):
    found = set(FUNC_REF_RE.findall(text))
    found |= set(SNAKE_RE.findall(text))
    found |= set(MACRO_RE.findall(text))
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-C", dest="src", default=".")
    ap.add_argument("--today", default=None,
                    help="YYYY-MM-DD for age; default: HEAD commit date")
    args = ap.parse_args()

    items = [json.loads(l) for l in sys.stdin if l.strip()]
    if args.today:
        today = args.today
    else:
        today = subprocess.run(["git", "-C", args.src, "log", "-1", "--format=%cs",
                                items[0]["head"]], check=True,
                               capture_output=True, text=True).stdout.strip()
    ty = int(today[:4]) + (int(today[5:7]) - 1) / 12

    wanted = set()
    in_markers = Counter()
    for it in items:
        it["_ids"] = ids_in(it["comment"])
        wanted |= it["_ids"]
        for i in it["_ids"]:
            in_markers[i] += len(re.findall(r"\b%s\b" % re.escape(i), it["comment"]))

    counts = Counter()
    if wanted:
        # ripgrep's multi-pattern search is minutes faster than git grep -F -f.
        if shutil.which("rg"):
            cmd = ["rg", "--no-filename", "--no-messages", "-o", "-w", "-F",
                   "-f", "-", "."]
        else:
            cmd = ["git", "grep", "-h", "-o", "-w", "-I", "-F", "-f", "/dev/stdin"]
        r = subprocess.run(cmd, cwd=args.src, input="\n".join(sorted(wanted)) + "\n",
                           capture_output=True, text=True, errors="replace")
        for tok in r.stdout.split("\n"):
            if tok:
                counts[tok] += 1

    for it in items:
        text = it["comment"]
        tb = sorted(set(m.group(0).lower() for m in TIMEBOUND_RE.finditer(text)))
        hi = sorted(set(m.group(0) for m in HISTORY_RE.finditer(text)))
        missing = sorted(i for i in it.pop("_ids") if counts[i] <= in_markers[i])
        bare = len(strip_markers(text)) < 12
        age = None
        if it.get("blame_date"):
            d = it["blame_date"]
            age = round(ty - (int(d[:4]) + (int(d[5:7]) - 1) / 12), 1)
        score = 3 * bool(missing) + 2 * bool(tb) + 2 * bool(hi)
        if age is not None:
            score += 2 if age >= 15 else (1 if age >= 7 else 0)
        if it["class"] == "vendor" or it["generated"]:
            score -= 5
        it.update({"timebound": tb, "history": hi, "missing_ids": missing,
                   "bare": bare, "age": age, "score": score})
        sys.stdout.write(json.dumps(it, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
