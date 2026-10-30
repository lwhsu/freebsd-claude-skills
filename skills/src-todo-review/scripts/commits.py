#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
"""Group applied comment edits into commits, one per component.

    commits.py plan  -C srcdir -l ledger.jsonl -e applied.jsonl -o outdir
    commits.py make  -C srcdir -o outdir [--trailer LINE ...]

"plan" groups the applied edits by component (the driver, library or
program, as a commit subject would name it; components with fewer than
--min edits are pooled by tree: sys/dev, sys, lib, bin, ...) and writes,
per group, outdir/<group>.md ("/" in a group name becomes "_"): the
items with the verdict, rationale and evidence behind each edit, and the
diff of the group's files.  A writer (person or subagent) then puts the
commit message in outdir/<group>.msg.

"make" commits each group that has a .msg file, in plan order, staging
only that group's files, and records the commits in outdir/commits.jsonl
({"sha", "subject", "ids", "files"}).
"""

import argparse
import json
import os
import subprocess
import sys
from collections import OrderedDict

# Path prefixes whose component name is not simply the last directory.
COMPONENTS = [
    ("lib/libc/", "libc"), ("lib/msun/", "msun"), ("lib/libthr/", "libthr"),
    ("sys/kern/", "kern"), ("sys/vm/", "vm"), ("sys/net/", "net"),
    ("sys/netinet/", "netinet"), ("sys/netinet6/", "netinet6"),
    ("sys/net80211/", "net80211"), ("sys/netpfil/pf/", "pf"),
    ("sys/netpfil/ipfw/", "ipfw"), ("sys/netgraph/", "netgraph"),
    ("sys/cam/", "cam"), ("sys/geom/", "geom"), ("sys/ufs/", "ufs"),
    ("sys/compat/linuxkpi/", "linuxkpi"), ("sys/compat/linux/", "linux"),
    ("sys/dev/sound/", "sound"), ("sys/dev/usb/", "usb"),
    ("sys/x86/", "x86"), ("sys/amd64/", "amd64"), ("sys/i386/", "i386"),
    ("sys/arm64/", "arm64"), ("sys/arm/", "arm"), ("sys/powerpc/", "powerpc"),
    ("sys/riscv/", "riscv"), ("sys/sys/", "sys"), ("share/man/", "man"),
    ("stand/", "loader"), ("tests/", "tests"), ("tools/", "tools"),
]


def component(path):
    for prefix, name in COMPONENTS:
        if path.startswith(prefix):
            return name
    parts = path.split("/")
    if parts[0] == "sys" and len(parts) > 3 and parts[1] == "dev":
        return parts[2]
    if parts[0] in ("bin", "sbin", "usr.bin", "usr.sbin", "libexec", "lib",
                    "cddl", "secure") and len(parts) > 2:
        return parts[1]
    return parts[-2] if len(parts) > 1 else parts[0]


def family(path):
    """Where a component too small for its own commit goes."""
    parts = path.split("/")
    if parts[0] == "sys":
        return "sys/dev" if len(parts) > 2 and parts[1] == "dev" else "sys"
    if parts[0] in ("lib", "libexec"):
        return "lib"
    if parts[0] in ("bin", "sbin", "usr.bin", "usr.sbin", "cddl", "secure"):
        return "usr.sbin" if parts[0] == "usr.sbin" else "bin"
    return "misc"


def plan(args):
    ledger = {}
    for line in open(args.ledger):
        if line.strip():
            r = json.loads(line)
            ledger[r["id"]] = r
    applied = [json.loads(l) for l in open(args.applied) if l.strip()]
    sizes = {}
    for e in applied:
        sizes[component(e["path"])] = sizes.get(component(e["path"]), 0) + 1

    def group(e):
        c = component(e["path"])
        return c if sizes[c] >= args.min else family(e["path"])

    groups = OrderedDict()
    for e in sorted(applied, key=lambda e: (group(e), e["path"], e["range"][0])):
        groups.setdefault(group(e), []).append(e)
    os.makedirs(args.out, exist_ok=True)
    order = []
    for name, es in groups.items():
        files = sorted(set(e["path"] for e in es))
        diff = subprocess.run(["git", "-C", args.src, "diff", "--"] + files,
                              capture_output=True, text=True).stdout
        base = name.replace("/", "_")
        with open(os.path.join(args.out, base + ".md"), "w") as f:
            f.write("# %s: %d edits in %d files\n\n" % (name, len(es), len(files)))
            for e in es:
                r = ledger[e["id"]]
                f.write("## %s %s:%d (%s)\n\n" % (e["id"], e["path"], r["line"], r["verdict"]))
                f.write("Rationale: %s\n\n" % r.get("rationale", ""))
                if r.get("evidence"):
                    f.write("Evidence:\n")
                    for ev in r["evidence"]:
                        f.write("- %s\n" % ev)
                    f.write("\n")
                if r.get("verify_notes"):
                    f.write("Second review: %s\n\n" % r["verify_notes"])
            f.write("## Diff\n\n```diff\n%s```\n" % diff)
        order.append({"group": name, "base": base, "ids": [e["id"] for e in es],
                      "files": files})
    with open(os.path.join(args.out, "plan.json"), "w") as f:
        json.dump(order, f, indent=1)
    print("%d edits in %d groups" % (len(applied), len(order)))


def make(args):
    with open(os.path.join(args.out, "plan.json")) as f:
        order = json.load(f)
    done = []
    for g in order:
        msgf = os.path.join(args.out, g["base"] + ".msg")
        if not os.path.exists(msgf):
            print("%s: no message, skipped" % g["group"], file=sys.stderr)
            continue
        with open(msgf) as f:
            msg = f.read().rstrip("\n") + "\n"
        if args.trailer:
            msg += "\n" + "\n".join(args.trailer) + "\n"
        subprocess.run(["git", "-C", args.src, "add", "--"] + g["files"], check=True)
        subprocess.run(["git", "-C", args.src, "commit", "-q", "-F", "-"],
                       input=msg, text=True, check=True)
        sha = subprocess.run(["git", "-C", args.src, "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
        done.append({"sha": sha, "subject": msg.split("\n")[0], "ids": g["ids"],
                     "files": len(g["files"])})
        print("%s %s" % (sha[:12], msg.split("\n")[0]))
    with open(os.path.join(args.out, "commits.jsonl"), "a") as f:
        for d in done:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["plan", "make"])
    ap.add_argument("-C", dest="src", default=".")
    ap.add_argument("-l", dest="ledger")
    ap.add_argument("-e", dest="applied", help="edits that apply.py applied")
    ap.add_argument("-o", dest="out", required=True)
    ap.add_argument("--trailer", action="append", default=[])
    ap.add_argument("--min", type=int, default=3,
                    help="components with fewer edits share a commit with "
                         "their neighbours (sys/dev, sys, lib, bin, ...)")
    args = ap.parse_args()
    plan(args) if args.cmd == "plan" else make(args)


if __name__ == "__main__":
    main()
