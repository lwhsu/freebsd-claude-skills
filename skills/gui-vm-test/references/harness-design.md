# Harness design

`gui-lib.sh` holds what is the same for every program; a harness holds what
is specific. `example-harness.sh` is a complete, working harness for xterm.

## What the library provides

| Function | Purpose |
|---|---|
| `gui_start`, `gui_stop` | Xvfb (`-noreset`), session D-Bus if installed, `DISPLAY`, `XDG_RUNTIME_DIR` |
| `wait_for <sec> <cmd...>` | poll a condition with an upper bound; every step uses it |
| `gui_wid`, `gui_title`, `gui_has_window <regex>` | find visible windows by title |
| `gui_key <regex> <key>`, `gui_type <regex> <text>` | focus the window (`--sync`), then send input |
| `gui_launch <cmd...>`, `gui_gone` | start the program (`GUI_PID`), test for exit |
| `gui_load_start <n>`, `gui_load_stop` | CPU contention with `yes` |
| `gui_freeze` | SIGSTOP the program: the positive control |
| `gui_snap <label>`, `gui_shot <label>` | thread list + kernel stacks, screenshot |
| `gui_fail <label>` | on timeout: evidence, classification, kill (kept with `GUI_KEEP_FAILED`); counts in `HANGS` |

## What the harness must define

1. **Start**, with a fixed configuration that turns off everything able to
   open an unexpected window or change behaviour: update checks, tray icon,
   first-run dialogs, idle locking, session restore. Create test data with
   the program's command-line tools so that every guest has the same.
2. **States seen from outside.** The window title is the simplest probe
   (`doc [Locked] - App` versus `doc - App`). Others: a window appearing or
   disappearing, a file being written, process exit, `xprop` properties.
   Do not modify the program to observe it.
3. **Actions** as key sequences (`ctrl+l`, typed text, `Return`). Prefer
   keyboard shortcuts over mouse coordinates.
4. **Probe key**: a shortcut that makes a healthy program exit
   (`GUI_PROBE_WIN`, `GUI_PROBE_KEY`). A program stuck in a blocking wait
   does not process it; a slow one does.
5. Optionally **`gui_app_evidence`** for the signature of the expected bug,
   for example a gdb command printing a variable in the frames of interest,
   or a check of which kernel wait the main thread sits in. Reject an
   unknown `MODE` instead of running nothing.

## Classification

| ps state / observation | Meaning | Next step |
|---|---|---|
| no process or zombie | exited or crashed | `app-stderr.log`, core file; often a test-environment problem |
| `T` | stopped by the self-check | expected in self-check runs only |
| alive, no window matches | start-up problem | screenshot, `app-stderr.log` |
| alive, exits on probe key | slow step, lost keystroke or focus problem | screenshot; raise timeout or fix the harness |
| alive, ignores probe key | hang | kernel stacks and gdb backtrace in `FAIL-*.txt` |

Test the probe key by hand in every state the program can be in: a key that
does not end a healthy program turns every slow step into a reported hang.
`gui_fail` collects in this order: process state, kernel stacks,
`gui_app_evidence`, screenshot, probe key, gdb. gdb comes last because
attaching can disturb a blocked process and detaching resumes a stopped one.

Without classification a launch failure counts as a hang and a correct fix
looks ineffective.

## Positive control

A result of "0 failures" is only worth something if the harness would have
reported a failure. `gui_freeze` before a step makes that step impossible;
the harness must report exactly that timeout, classify it STOPPED, and the
following normal cycle must pass (the environment survived). Run it on every
guest before the real runs and state the result in the report.

## Modes worth having

- full cycle in a fresh process each time (start-up paths);
- many repetitions of the critical step in one process, with and without
  load (the main test for races);
- alternative paths to the same step (command-line option, different entry
  point), quit from each state;
- an untimed inspection run with gdb/truss attached, to learn what normal
  looks like before judging failures.

Select them with environment variables (`MODE=`, counts, `LOAD=`), so that
`run.sh` records the exact invocation in `ident.txt`.

## Driving from the host

Runs last minutes to hours. Start them with `nohup ... &` over ssh and poll
`keep/<tag>/done`; do not keep an ssh session open for the run. For a chain
of runs, write a small script in the guest that calls `run.sh` for each and
stops at the first unexpected `TIMEOUT` in `harness.log`.
