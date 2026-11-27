# Pitfalls

All of these cost time in real runs.

## Xvfb

- **Start Xvfb with `-noreset`.** By default it resets when its last client
  disconnects and refuses new connections meanwhile. Each xdotool call is a
  client, so the program under test fails to start at random with "could not
  connect to display" and the harness records a timeout. Measured with two
  loops of 300 xdotool calls: 131 and 165 failures without the flag, 0 with.
  `gui-lib.sh` sets it.
- There is no window manager. `xdotool windowfocus` works without one, but a
  program that needs one (window activation, maximising, some dialogs) needs
  a small window manager started in the harness. Not exercised here.
- Install a font package (`dejavu`); toolkits may show empty text without.
- Qt programs: set `QT_QPA_PLATFORM=xcb` if the program could pick Wayland.

## Processes

- **FreeBSD `timeout(1)` waits for all descendants.** `timeout 900 sh
  harness.sh` sat for the whole 900 s waiting for the background Xvfb. Use
  the per-step `wait_for` and the detached run with a done marker.
- **Detaching gdb resumes a SIGSTOPped process.** Read the process state with
  `ps` before attaching gdb, or the self-check is misclassified.
  `gui_fail` does it in that order.
- An interrupted harness used to leave Xvfb behind, and the next run then
  used the old server with its old windows. `gui_start` now refuses a
  display that already answers, and traps clean up.
- `date +%N` needs FreeBSD 14.1 or newer; on older guests the step times in
  the log are whole seconds.
- `$!` after starting a wrapper script is the wrapper, not the program. Set
  `GUI_PID` from `pgrep` when the real process is a child.
- A second instance may hand over to a running one and exit (single-instance
  programs). Kill leftovers and remove their sockets/lock files before each
  launch.
- **Gone is not the same as exited cleanly.** A program that crashes on the
  way out passes a `wait_for ... gui_gone` step. Call `gui_reap` after it
  (exit status; `gui_crash` counts the failure in `CRASHES`). Without it a
  SIGSEGV on quit was counted as a pass. The kernel logs such crashes as
  "exited on signal 11" (`dmesg`), but only for signals that dump core.
- The default core size limit may be 0; `KEEP_CORES=1` for `run.sh`
  collects cores in `keep/<tag>/cores`. With the common
  `kern.corefile=%N.core` every crash overwrites the previous core, so a
  harness that expects more than one should change into a directory per
  cycle before starting the program (the core goes to the crashing
  process's working directory). Do not change the host's sysctl.
- A rare crash may only show up with different timing. One second-instance
  crash appeared only with `ktrace` attached (1 in 200 handovers, 0 in 200
  without). A tight loop around the suspect step finds it faster than full
  cycles.
- A window title can be set before the program processes input (web
  frontends: the native title first, the page title later). Restrict
  `GUI_PROBE_WIN` to titles in which the probe key really works, so that a
  start-up stuck earlier is classified NO WINDOW, not UNRESPONSIVE.

## Chromium and Electron programs

- **Drive them with the DevTools protocol (CDP), judge them from
  outside.** Start the program with `--remote-debugging-port=<port>
  --remote-debugging-address=127.0.0.1` (how to pass Chromium flags
  depends on the program; Electron apps often take an environment
  variable). A small client using `Runtime.evaluate`,
  `Input.dispatchMouseEvent` and `Input.insertText`, finding elements by
  `data-testid` or accessible name, is much more reliable than screen
  coordinates; `scripts/guest/cdp.mjs` is such a client (Node 22 or
  newer, no modules). Keep pass/fail on outside observations (window title,
  side effects such as requests seen by a test server), not on CDP.
- **Every CDP call needs a timeout that covers connecting.** A stopped
  or hung browser process accepts the TCP connection on the debugging
  port but never answers the HTTP or WebSocket handshake, so a
  per-command timeout is not enough. The self-check found this: the
  harness hung instead of reporting the frozen step. A key press that
  starts a navigation may also get no reply.
- **Children can inherit the debugging listening socket.** Helper
  processes the program spawns (a background service it manages) were
  seen holding it. A helper left over from a killed cycle keeps the
  port: the next instance cannot bind it and CDP clients hang. Kill the
  helpers with the program and check the port is free (`sockstat -4l`)
  before each launch.
- The debugging port is open to every local user while it listens (and
  to `ip4=inherit` jails): open it only during runs.
- Network I/O is done by a separate utility process (the network
  service), not by `GUI_PID`. Per-socket checks (sockstat) see that pid.
- On other platforms than macOS no key may quit the program (the quit
  menu role is macOS only). Use `gui_app_probe` for the probe, for
  example a click on the program's own close button with
  `xdotool mousemove --window <wid> <x> <y> click 1`.
- **Session restore reloads the last page at start-up.** A restarted
  program fetched the previous cycle's page again. Make per-cycle
  markers unique per run (a run prefix) and match them exactly, so that
  requests from earlier runs, or `c10` when looking for `c1`, are never
  counted. Without it a check "all N subresources arrived" was
  satisfied by an earlier run's log lines.

## Load and timing

- **Match the number of `yes` jobs to the vCPU count.** On an 8 vCPU guest,
  4 jobs gave 0 failures in 30 runs of a build with a known race; 8 jobs gave
  30 of 30. Always report vCPUs and load together.
- `xdotool type --delay 30` keeps keystrokes from being dropped under load.
- A step that normally takes under a second took about 4 s under full load;
  timeouts of 20 to 30 s kept false positives away.

## Packages and versions

- A package built on a newer minor release may not run on an older one of
  the same branch (new symbol versions in base libraries). Build on the
  oldest supported minor, or use official packages for the dependencies.
- `poudriere bulk -NN` leaves packages in `.building/All` without a
  repository catalogue; a guest cannot use that directory as a pkg
  repository. Copy the package file in and use `guest-setup.sh -f`.
- Verify what is installed before every run (`run.sh` identity). It is easy
  to test yesterday's package all day.

## Images and network

- Snapshot `CHECKSUM.SHA256` files use dated file names; search for the hash.
- After writing an image into a larger disk file, run `gpart recover` on it;
  `growfs_enable` extends the file system on first boot. `mkvm.sh` does this.
- Find the root partition by type (`gpart show -p`), not by number.
- Without NAT, do not change the host firewall; use `proxy.py`, bound to the
  switch address only and limited to the needed domains (and to ports 80
  and 443, public addresses). Host names are compared case-insensitively
  (`pkg.FreeBSD.org`). It does not check who connects.
- pkg resolves an SRV record even behind a proxy; with no nameserver in the
  guest it fails with "No SRV record found" and "pkg+:// implies SRV mirror
  type".
- A shell `trap` that runs under `set -e` stops at its first failing
  command; cleanup traps must not rely on every command succeeding.
  FreeBSD sh does not run the EXIT trap on SIGTERM/SIGHUP unless those are
  trapped too, and `a | b` under `set -e` hides a failing `a` without
  `set -o pipefail`.

## Evidence

- Copy results out of the guest and check they arrived before destroying it.
  Leave the large `.xwd` screenshots unless needed (`xwdtopnm` or
  `convert` reads them).
- Stop at the first unexpected failure and use a new tag for every run:
  `run.sh` writes into `keep/<tag>`, and a rebooted or reinstalled guest
  loses cores and process state.
