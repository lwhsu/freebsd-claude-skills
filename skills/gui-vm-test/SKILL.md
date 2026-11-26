---
description: "Test a GUI program on FreeBSD without a display by driving it under Xvfb with xdotool inside a throwaway bhyve VM, with a self-check that proves the test can see a failure. This skill should be used when a port or program with a GUI must be run, not only built: checking for hangs, crashes or wrong behaviour on one or several FreeBSD versions, reproducing a GUI bug report, or verifying a fix on a kernel/base version other than the host's."
user_invocable: true
arguments: "<category/portname or program> [FreeBSD versions]"
---

# GUI Test in a bhyve VM

Run a GUI program on a virtual screen (Xvfb) in a throwaway FreeBSD guest,
drive it with simulated keystrokes (xdotool), and decide pass/fail from what
can be observed from outside: window titles, process state, exit.

The answer must be trustworthy. That takes four things, none optional:

1. **Identity**: prove the guest runs the package you think it runs.
2. **Positive control (self-check)**: prove the harness reports a failure when
   one happens.
3. **Classification**: every timeout is sorted into stopped / gone / alive, so
   a test-environment problem is not reported as the bug.
4. **Control build** (when the claim is "this change fixes it"): the same test
   on a build without the change must fail.

Scripts are in `scripts/` next to this file (`host/` runs on the host,
`guest/` is copied into the guest). The commands below use `$S` for that
directory and `$W` for your work directory; set both to absolute paths first
(the current directory is usually a source tree, not the skill). Read `references/pitfalls.md` before the
first run and `references/harness-design.md` before writing a harness.

## When a VM, when not

- VM: another FreeBSD version or branch than the host, anything touching the
  kernel or base libraries, scheduling/race problems (real vCPUs), tests that
  must not disturb the host.
- A jail with Xvfb is enough when the host's kernel and base are the right
  ones. The guest scripts do not depend on bhyve, but this skill has only
  been exercised in VMs.

## Rules for a shared host

- sudo only for your own guests: `vm` on guests you created, `mdconfig`,
  `mount`/`umount` and `dd` on your own images. Ask the user first if sudo
  for this has not been agreed in the project.
- Never touch other guests, switches, firewall, rc.conf or kernel modules.
- Clean up guests, md devices, helper servers and keys when done.

## Procedure

### 1. Discover the host

```sh
sudo vm list                 # existing guests: note them, do not touch
sudo vm switch list          # switch name and host address (the guests' gateway)
sysrc -n vm_dir              # where guests live
kldstat | grep -E 'vmm|pf'   # vmm must be loaded; pf tells whether NAT is possible
sockstat -4l | grep ':53 '   # is there a DNS forwarder on the switch address?
```

Needed: `sysutils/vm-bhyve`, `sysutils/edk2-bhyve`, a switch. If something is
missing, tell the user; do not set up host networking yourself.

Pick a guest name, a free address on the switch network (`ping` it first) and
a work directory for images and results (not a shared temp directory).

Guest Internet access: if the host does not NAT the switch network, run
`python3 $S/host/proxy.py <switch-address> <port> &` (any Python 3; the
interpreter may be installed as `python3.N` only) and give the guest
`HTTP_PROXY`/`HTTPS_PROXY`. The proxy only reaches `*.freebsd.org` on ports
80 and 443 unless more suffixes are given, but every guest on the switch can
use it, so stop it when done. pkg still needs DNS for its SRV lookup, so the
guest needs a nameserver it can reach (commonly a forwarder on the switch
address).

### 2. Get an image and verify it

Official images: `https://download.freebsd.org/releases/VM-IMAGES/<rel>/amd64/Latest/`
and `https://download.freebsd.org/snapshots/VM-IMAGES/` (stable, current).
Take the UFS raw image (`...-amd64-ufs.raw.xz`; branches before 14 name it
`...-amd64.raw.xz`).

```sh
B=https://download.freebsd.org/releases/VM-IMAGES/15.1-RELEASE/amd64/Latest
f=FreeBSD-15.1-RELEASE-amd64-ufs.raw.xz
cd $W && fetch $B/$f
h=$(sha256 -q $f); fetch -qo - $B/CHECKSUM.SHA256 | grep -- "$h"
```

Look the hash up rather than the file name: snapshot checksum files use dated
names, and the match gives the snapshot date and src revision. Record them.

### 3. Create the guest

```sh
ssh-keygen -q -t ed25519 -N '' -f $W/id_test          # throwaway key, per test
NAMESERVER=<dns> sh $S/host/mkvm.sh <name> $W/$f <ip/prefix> <gateway> <switch> $W/id_test.pub
sudo vm start <name>
export GUI_TEST_KEY=$W/id_test
for i in $(seq 1 40); do sh $S/host/gssh.sh <ip> true 2>/dev/null && break; sleep 5; done
```

If `mkvm.sh` fails after creating the guest it says so; destroy that guest
before retrying.

`mkvm.sh` defaults to 4 vCPU, 4 GB, 20 GB (`CPU=`, `MEM=`, `DISK=`). Give more
when building inside the guest. Record the vCPU count: load tests depend on it.

### 4. Install tools and the software under test

```sh
sh $S/host/gssh.sh -c $S/guest/*.sh root@<ip>:/root/
sh $S/host/gssh.sh <ip> 'env HTTP_PROXY=... HTTPS_PROXY=... sh /root/guest-setup.sh <options>'
```

`guest-setup.sh` installs the test tools; the example harness also needs
`-o xterm`. How the package under test gets in (one package per option,
options may repeat, processed in order):

- `-r http://<gateway>:<port>/<repo> -l <pkg>`: from a poudriere repository
  served by the host (`python3 -m http.server --bind <gateway> <port> -d <dir>`
  where `<dir>/<repo>` is a symlink to the repository directory). Priority
  100 makes its dependencies come from the same build. Needs a repository
  catalogue; after `poudriere bulk -NN` the packages sit in `.building/All`
  without one. When a proxy is set, add `NO_PROXY=<gateway>` so that this
  repository is fetched directly.
- `-f /root/<file>.pkg`: a package file copied in with `gssh.sh -c`
  (replaces an installed package of that name); dependencies come from the
  official repository.
- `-o <pkg>`: from the official repository.
- Build in the guest from a ports tree copy when the host cannot build for
  that version (`git archive HEAD | gssh.sh <ip> 'mkdir -p /usr/ports && tar -xf - -C /usr/ports'`,
  then `make install-missing-packages` and `make package`).

Build packages on the oldest supported minor release of a branch; packages
built on a newer minor may not run on an older one.

### 5. Write the harness

Copy `scripts/guest/example-harness.sh` and replace its three marked parts:
how to start the program with every pop-up disabled, how each state looks
from outside, and a key that makes a healthy program exit. Keep the
structure: each step is `action; wait_for <timeout> <condition> || { gui_fail <label>; return; }`.

Choose timeouts far above the slowest normal time measured under load.
If the failure has an application-specific signature (for example which
function the main thread waits in), add a `gui_app_evidence` function.

### 6. Check identity, then self-check, then test

Always start runs through `run.sh`, detached, and poll the done marker:

```sh
sh $S/host/gssh.sh <ip> 'nohup sh /root/run.sh <tag> /root/<harness>.sh MODE=... \
    IDENT_PKGS="<pkg> <deps>" IDENT_FILES=/usr/local/bin/<prog> "IDENT_CHECK=<command>" >/dev/null 2>&1 &'
until r=$(sh $S/host/gssh.sh <ip> "cat /root/keep/<tag>/done 2>/dev/null"); [ -n "$r" ]; do sleep 30; done
echo "$r"; sh $S/host/gssh.sh <ip> "cat /root/keep/<tag>/summary.txt"
```

- Every argument after the harness must be `VAR=VALUE`; quote the whole
  argument when the value has spaces. Use a new tag for each run.
- A run counts only if `done` says `done rc=0` and `summary.txt` has the
  `SUMMARY` line(s) with the expected numbers. `MISMATCH`, `USAGE`, a
  non-zero rc or an empty summary mean the test did not run; read
  `ident.txt` and `harness.log`.
- `ident.txt` records uname, package versions and origin repository, and
  sha256 of the binaries. Compare the hash with the host's package. Give
  `IDENT_CHECK` whenever two builds can be told apart mechanically
  (`nm -D`, `strings`, a version output); `run.sh` refuses to run on mismatch.
- Run the self-check (`MODE=selftest`) on every guest before the real runs.
  It freezes the program with SIGSTOP and expects exactly the announced
  number of timeouts, classified STOPPED, and a clean cycle afterwards.
- Then the real runs: enough repetitions, and with CPU load
  (`LOAD=<vCPU count>`) when timing could matter. Do not wrap a run in
  `timeout(1)`.
- Stop at the first unexpected timeout and keep the guest as it is until the
  evidence is copied out. In the example harness `STOP_ON_FAIL=1` ends the
  cycles there and leaves the program and Xvfb running for inspection
  (`pkill Xvfb dbus-daemon` before the next run).
- Read the classification of every timeout before calling it the bug:
  GONE means exit or crash (check `app-stderr.log`, cores), ALIVE NO WINDOW
  a start-up problem, ALIVE RESPONSIVE slow or an input problem (look at
  the screenshot). Only ALIVE UNRESPONSIVE is a hang.

### 7. Control build

When reporting "fixed": install a build without the fix in the same guest
(`guest-setup.sh -f`), make `IDENT_CHECK` prove which one is installed, and run the
same test with the same load. A fix result means something only if the
control fails there. If the control does not fail, raise repetitions and
load before concluding anything.

### 8. Collect, then clean up

```sh
mkdir -p $W/evidence
sh $S/host/gssh.sh <ip> 'tar -czf - --exclude "*.xwd" -C /root keep' | tar -xzf - -C $W/evidence
```

Check the files arrived, then:

```sh
sudo vm poweroff -f <name>      # wait for "Stopped" in `sudo vm list`
sudo vm destroy -f <name>
kill <proxy and http.server pids>; rm $W/id_test $W/id_test.pub
sudo vm list; sudo mdconfig -l; zfs list -r <vm dataset>; sockstat -4l | grep <gateway>
```

Only the pre-existing guests and services may remain.

### 9. Report

State exactly what was run: FreeBSD version and revision of each guest, vCPU
count, load, number of cycles, number of timeouts and their classification,
self-check result, control result, package version and hash. "Tested" alone
is not a result.
