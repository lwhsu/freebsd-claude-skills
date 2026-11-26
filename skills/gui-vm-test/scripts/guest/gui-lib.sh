# gui-lib.sh - helpers for driving a GUI program under Xvfb with xdotool.
# Source it from an application-specific harness (see example-harness.sh).
# Runs in the guest as root with /bin/sh.
#
# Variables (set before gui_start to override):
#   GUI_DISPLAY (:1)  GUI_SCREEN (1280x1024x24)  GUI_OUT ($HOME/gui-out)
#   GUI_KEEP_DISPLAY (unset)  set to make gui_stop leave Xvfb and D-Bus running
#   GUI_KEEP_FAILED (unset)   set to keep a timed-out program instead of
#                              killing it, for inspection by hand
# Optional, defined by the harness:
#   gui_app_evidence <label>   extra evidence for a timeout; runs first,
#                              before the probe key and before gdb attaches
#   GUI_PROBE_WIN, GUI_PROBE_KEY   window regex and key that make a healthy
#                              program exit; used to tell "slow" from "stuck"

: "${GUI_DISPLAY:=:1}" "${GUI_SCREEN:=1280x1024x24}" "${GUI_OUT:=$HOME/gui-out}"
HANGS=0
CRASHES=0
GUI_PID=
_gui_load=

gui_log() { echo "[$(date +%H:%M:%S)] $*"; }
# %N needs FreeBSD 14.1 or newer; older guests only time whole seconds.
gui_now() { date +%s.%N | sed 's/\.N$/.0/'; }
gui_el() { echo "$1 $2" | awk '{ printf "%.2f", $2 - $1 }'; }

# wait_for <seconds> <command...>: poll until the command succeeds.
wait_for() {
	_t=$1; shift
	_end=$(($(date +%s) + _t))
	while [ "$(date +%s)" -lt "$_end" ]; do
		"$@" && return 0
		sleep 0.2
	done
	return 1
}

gui_start() {
	mkdir -p "$GUI_OUT"
	export DISPLAY=$GUI_DISPLAY XDG_RUNTIME_DIR=/tmp/gui-rt-$(id -u)
	mkdir -p -m 700 "$XDG_RUNTIME_DIR"
	# A server left over from an interrupted run would be reused silently,
	# with its old windows and load.
	if xdpyinfo > /dev/null 2>&1; then
		gui_log "display $DISPLAY is already in use (leftover Xvfb?)"
		exit 1
	fi
	trap gui_stop EXIT
	trap 'exit 1' INT TERM HUP
	# -noreset: without it Xvfb resets when its last client disconnects
	# and refuses connections meanwhile, so launches fail at random.
	Xvfb "$GUI_DISPLAY" -screen 0 "$GUI_SCREEN" -nolisten tcp -noreset \
	    > "$GUI_OUT/xvfb.log" 2>&1 &
	_gui_xvfb=$!
	{ wait_for 20 xdpyinfo > /dev/null 2>&1 && kill -0 "$_gui_xvfb" 2>/dev/null; } ||
	    { gui_log "Xvfb did not start, see $GUI_OUT/xvfb.log"; exit 1; }
	if command -v dbus-launch > /dev/null; then
		eval "$(dbus-launch --sh-syntax)"
	fi
	gui_log "display $DISPLAY up, dbus ${DBUS_SESSION_BUS_ADDRESS:-none}"
}

gui_stop() {
	gui_load_stop
	if [ -n "$GUI_KEEP_DISPLAY" ]; then
		gui_log "GUI_KEEP_DISPLAY set: Xvfb and D-Bus left running (pkill Xvfb dbus-daemon before the next run)"
		return
	fi
	[ -z "$DBUS_SESSION_BUS_PID" ] || kill "$DBUS_SESSION_BUS_PID" 2>/dev/null
	DBUS_SESSION_BUS_PID=
	if [ -n "$_gui_xvfb" ]; then
		kill "$_gui_xvfb" 2>/dev/null
		wait "$_gui_xvfb" 2>/dev/null
		_gui_xvfb=
	fi
}

# Windows are found by a regular expression on the title.
gui_wid() { xdotool search --onlyvisible --name "$1" 2>/dev/null | head -1; }
gui_title() { xdotool search --onlyvisible --name "$1" getwindowname %@ 2>/dev/null | head -1; }
gui_has_window() { [ -n "$(gui_wid "$1")" ]; }

# gui_key <window-regex> <key>      e.g. gui_key ' - MyApp$' ctrl+q
gui_key() {
	xdotool windowfocus --sync "$(gui_wid "$1")" 2>/dev/null
	xdotool key "$2"
}
# gui_type <window-regex> <text>    the delay keeps keys from being dropped under load
gui_type() {
	xdotool windowfocus --sync "$(gui_wid "$1")" 2>/dev/null
	xdotool type --delay 30 "$2"
}

# gui_launch <command...>: start the program, remember its pid in GUI_PID.
# If the command is a wrapper script that execs or forks the real program,
# set GUI_PID yourself afterwards (pgrep -n -x <name>).
gui_launch() {
	"$@" >> "$GUI_OUT/app-stderr.log" 2>&1 &
	GUI_PID=$!
}
gui_gone() { ! kill -0 "$GUI_PID" 2>/dev/null; }
# gui_reap: after gui_gone, read the exit status of GUI_PID (started by
# gui_launch, so a child of this shell).  Sets GUI_EXIT to "exit N" or
# "signal N"; succeeds only for "exit 0".  gui_gone alone cannot tell a
# clean exit from a crash on the way out.
gui_reap() {
	wait "$GUI_PID" 2>/dev/null
	_rc=$?
	if [ "$_rc" -gt 128 ]; then GUI_EXIT="signal $((_rc - 128))"; else GUI_EXIT="exit $_rc"; fi
	[ "$_rc" = 0 ]
}
# gui_crash <label>: the program ended, but not with exit 0.  Counted in
# CRASHES, separately from the timeouts in HANGS.
gui_crash() {
	CRASHES=$((CRASHES + 1))
	gui_log "  !!! CRASH at $1 (pid $GUI_PID): $GUI_EXIT; see app-stderr.log and cores"
}
gui_nthreads() { procstat -t "$GUI_PID" 2>/dev/null | tail -n +2 | wc -l | tr -d ' '; }

# gui_freeze: stop the program so that the next step must time out.  This is
# the positive control: a harness that does not report it cannot detect hangs.
gui_freeze() { gui_log "  SELFTEST: kill -STOP $GUI_PID"; kill -STOP "$GUI_PID"; }

gui_shot() { xwd -root -silent > "$GUI_OUT/$1.xwd" 2>/dev/null; }
gui_snap() {
	{ procstat -t "$GUI_PID"; echo; procstat -kk "$GUI_PID"; } > "$GUI_OUT/$1.txt" 2>&1
}

# CPU load: one `yes` per requested job.  Match the count to the guest's
# vCPUs (sysctl -n hw.ncpu), fewer does not create contention.
gui_load_start() {
	_j=0
	while [ "$_j" -lt "$1" ]; do
		yes > /dev/null &
		_gui_load="$_gui_load $!"
		_j=$((_j + 1))
	done
}
gui_load_stop() {
	[ -z "$_gui_load" ] || kill $_gui_load 2>/dev/null
	_gui_load=
}

# gui_fail <label>: a step timed out.  Collect evidence, classify, kill.
# Order matters: process state first (detaching gdb resumes a stopped
# process), the probe key before gdb (attaching can interrupt a blocked
# wait), gdb last.
gui_fail() {
	HANGS=$((HANGS + 1))
	_f=$GUI_OUT/FAIL-$1.txt
	gui_log "  !!! TIMEOUT at $1 (pid $GUI_PID), evidence in $_f"
	_st=$(ps -o state= -p "$GUI_PID" 2>/dev/null | tr -d ' ')
	_first=$(procstat -kk "$GUI_PID" 2>/dev/null | sed -n 2p)
	{
		echo "== TIMEOUT $1 at $(date)"
		ps -o pid,state,%cpu,time,wchan,command -p "$GUI_PID"
		echo; procstat -t "$GUI_PID"; echo; procstat -kk "$GUI_PID"; echo
		xwininfo -root -tree 2>&1 | head -60
	} > "$_f" 2>&1
	case $_st in
	''|Z*) ;;
	*)
		if command -v gui_app_evidence > /dev/null; then
			{ echo "== gui_app_evidence"; gui_app_evidence "$1"; } >> "$_f" 2>&1
		fi
		;;
	esac
	gui_shot "FAIL-$1" && gui_log "  screenshot $GUI_OUT/FAIL-$1.xwd"
	case $_st in
	''|Z*) _cls="GONE: the process exited or crashed (see app-stderr.log, look for a core)" ;;
	T*) _cls="STOPPED: self-check signature (SIGSTOP)" ;;
	*)
		if [ -z "$GUI_PROBE_KEY" ]; then
			_cls="ALIVE (no probe key defined)"
		elif ! gui_has_window "$GUI_PROBE_WIN"; then
			_cls="ALIVE, NO WINDOW: nothing matches '$GUI_PROBE_WIN' (start-up problem; see screenshot and app-stderr.log)"
		else
			gui_key "$GUI_PROBE_WIN" "$GUI_PROBE_KEY"
			if wait_for 15 gui_gone; then
				_cls="ALIVE, RESPONSIVE: exited on $GUI_PROBE_KEY (slow step, or input/focus problem)"
			else
				_cls="ALIVE, UNRESPONSIVE: no exit on $GUI_PROBE_KEY within 15s (hang)"
			fi
		fi
		;;
	esac
	if kill -0 "$GUI_PID" 2>/dev/null && command -v gdb > /dev/null; then
		{
			echo "== gdb"
			gdb -batch -nx -ex 'set pagination off' -ex 'info threads' \
			    -ex 'thread apply all bt' -p "$GUI_PID"
		} >> "$_f" 2>&1
	fi
	gui_log "  classification: state=${_st:-none}; $_cls"
	gui_log "  first listed thread kstack: ${_first:-none}"
	if [ -n "$GUI_KEEP_FAILED" ]; then
		gui_log "  GUI_KEEP_FAILED set: pid $GUI_PID left as it is"
	else
		kill -9 "$GUI_PID" 2>/dev/null
		sleep 1
	fi
}
