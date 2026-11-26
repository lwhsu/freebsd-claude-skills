#!/bin/sh
# Example harness: drives xterm.  Copy it and replace the three marked parts
# for a real program.  The state is read from the window title:
#   gui-test-start  ->  type "ready" + Return  ->  gui-test-ready
#   -> Return -> the program exits.
#
# usage: [MODE=all|selftest|cycles] [NCYC=5] [LOAD=0] [STOP_ON_FAIL=1] sh example-harness.sh
# Needs xterm in the guest (guest-setup.sh -o xterm).
# STOP_ON_FAIL=1: end the cycles at the first timeout and leave that process
# alone, so that the state can be inspected.
. "$(dirname "$0")/gui-lib.sh"

T_OPEN=${T_OPEN:-30}; T_STEP=${T_STEP:-15}; T_QUIT=${T_QUIT:-15}

# (1) How to start the program, with everything that could pop up a dialog
#     turned off (update checks, tray icons, first-run wizards).
start_app() {
	gui_launch xterm -T gui-test-start -e sh -c \
	    'read x || exit; printf "\033]0;gui-test-%s\007" "$x"; read y'
}
# (2) How each state looks from outside.
WIN='^gui-test-'
is_started() { gui_has_window '^gui-test-start$'; }
is_ready() { gui_has_window '^gui-test-ready$'; }
# (3) A key that makes a healthy program exit, for the responsiveness probe.
GUI_PROBE_WIN=$WIN
GUI_PROBE_KEY=ctrl+d

# cycle <label> [freeze]: one start/step/quit cycle; "freeze" is the self-check.
cycle() {
	lab=$1
	gui_log "--- cycle $lab ${2:+(selftest)}"
	t0=$(gui_now); start_app
	wait_for "$T_OPEN" is_started || { gui_fail "$lab-open"; return; }
	t1=$(gui_now)
	[ "$2" != freeze ] || gui_freeze
	gui_type "$WIN" ready; gui_key "$WIN" Return
	wait_for "$T_STEP" is_ready || { gui_fail "$lab-step"; return; }
	t2=$(gui_now)
	gui_key "$WIN" Return
	wait_for "$T_QUIT" gui_gone || { gui_fail "$lab-quit"; return; }
	t3=$(gui_now)
	gui_reap || gui_crash "$lab-quit"
	gui_log "  RESULT $lab: open=$(gui_el $t0 $t1) step=$(gui_el $t1 $t2) quit=$(gui_el $t2 $t3)"
}

case ${MODE:-all} in
all|selftest|cycles) ;;
*) gui_log "unknown MODE=$MODE (all, selftest, cycles)"; exit 64 ;;
esac
gui_log "=== $(uname -a)"
gui_start
case ${MODE:-all} in
selftest)
	cycle selftest freeze
	cycle post1
	gui_log "=== SUMMARY selftest: timeouts=$HANGS (expected 1) crashes=$CRASHES"
	;;
cycles|all)
	[ "${LOAD:-0}" = 0 ] || gui_load_start "$LOAD"
	GUI_KEEP_FAILED=${STOP_ON_FAIL:+1}
	i=1
	while [ $i -le "${NCYC:-5}" ]; do
		cycle "c$i"
		if [ -n "$STOP_ON_FAIL" ] && [ "$HANGS" -gt 0 ]; then
			gui_log "=== STOP_ON_FAIL: stopping after c$i"
			GUI_KEEP_DISPLAY=1
			break
		fi
		i=$((i + 1))
	done
	gui_load_stop
	real=$HANGS
	# cycles actually run: STOP_ON_FAIL may end the loop early
	ran=$(( i > ${NCYC:-5} ? ${NCYC:-5} : i ))
	gui_log "=== SUMMARY cycles: n=$ran/${NCYC:-5} load=${LOAD:-0} timeouts=$real (expected 0) crashes=$CRASHES (expected 0)"
	GUI_KEEP_FAILED=
	if [ "${MODE:-all}" = all ] && [ "$i" -gt "${NCYC:-5}" ]; then
		cycle selftest freeze
		cycle post1
		gui_log "=== SUMMARY selftest: timeouts=$((HANGS - real)) (expected 1)"
	fi
	;;
esac
gui_stop
gui_log "=== done"
