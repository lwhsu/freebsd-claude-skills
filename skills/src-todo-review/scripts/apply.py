#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
"""Apply REMOVE/REWORD edits to a src tree and prove they touch only comments.

    apply.py -C srcdir [-n] < edits.jsonl

Each edit is {"id", "path", "range": [first, last], "replacement"}, with
line numbers of the file at the inventory's HEAD.  Edits to one file are
applied bottom-up.  Afterwards the file's text with all comments removed
must split into the same tokens as before; a file that fails this check,
or whose edits overlap, is left untouched and reported.  Manual page text
is not a comment, so edits to it are only reported for a human to check.

Prints one line per edit: "applied", or "skipped: <reason>".  With -n,
checks without writing.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inventory  # noqa: E402


def strip_comments(text, lang):
    # Join continued lines first, as cpp(1) and make(1) do, so that a deleted
    # line that held only a comment and a backslash is not a change.
    if lang != "roff":
        text = text.replace("\\\n", "")
    if lang in ("c", "asm", "semi", "unknown", "lua", "sgml"):
        com = inventory.Comments(text, lang)
        out, pos = [], 0
        for s, e, _ in com.spans:
            out.append(text[pos:s])
            out.append(" ")
            pos = e
        out.append(text[pos:])
        text = "".join(out)
        if lang not in ("asm", "semi", "unknown"):
            return text.split()
    lines = text.split("\n")
    res = []
    for ln in lines:
        if lang == "roff":
            c = inventory.roff_comment_col(ln)
        elif lang == "asm":
            c = inventory.asm_comment_col(ln, len(ln))
        else:
            c = inventory.hash_comment_col(ln, lang if lang != "unknown" else "hash")
        res.append(ln[:c] if c >= 0 else ln)
    return "\n".join(res).split()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-C", dest="src", default=".")
    ap.add_argument("-n", dest="dry", action="store_true")
    args = ap.parse_args()

    edits = defaultdict(list)
    for line in sys.stdin:
        if line.strip():
            e = json.loads(line)
            edits[e["path"]].append(e)

    for path, es in sorted(edits.items()):
        fn = os.path.join(args.src, path)
        with open(fn, encoding="utf-8", errors="surrogateescape") as f:
            old = f.read()
        lines = old.split("\n")
        lang = inventory.lang_of(path, lines[0] if lines else "")
        es.sort(key=lambda e: e["range"][0], reverse=True)
        reason = None
        for a, b in zip(es, es[1:]):
            if b["range"][1] >= a["range"][0]:
                reason = "overlaps %s" % b["id"]
        for e in es:
            s, t = e["range"]
            if not (1 <= s <= t <= len(lines)):
                reason = "range %d-%d outside file" % (s, t)
        if lang == "roff" and any(e.get("doctext") for e in es):
            reason = "manual page text: check by hand"
        new = None
        if reason is None:
            for e in es:
                s, t = e["range"]
                rep = e["replacement"]
                repl = rep.split("\n") if rep != "" else []
                if repl and repl[-1] == "" and rep.endswith("\n"):
                    repl.pop()
                lines[s - 1:t] = repl
            new = "\n".join(lines)
            if strip_comments(old, lang) != strip_comments(new, lang):
                reason = "would change non-comment text"
        for e in sorted(es, key=lambda e: e["range"][0]):
            if reason:
                print("%s %s:%d-%d skipped: %s" % (e["id"], path, e["range"][0],
                                                  e["range"][1], reason))
            else:
                print("%s %s:%d-%d applied" % (e["id"], path, e["range"][0],
                                              e["range"][1]))
        if reason is None and not args.dry:
            with open(fn, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(new)


if __name__ == "__main__":
    main()
