#!/bin/sh
# Run one harness invocation, record what was tested, keep the results.
#
# usage: run.sh <tag> <harness.sh> [VAR=VALUE ...]
# Results go to $HOME/keep/<tag>/ (a tag cannot be reused).  The file "done"
# appears last and holds one line:
#   done rc=<harness exit status>   the harness ran; read summary.txt
#   MISMATCH                        the identity check refused the run
#   USAGE                           bad arguments
#
# Identity (set as VAR=VALUE arguments or in the environment):
#   IDENT_PKGS    packages whose version and repository are recorded
#   IDENT_FILES   files whose sha256 is recorded (compare with the host)
#   IDENT_CHECK   shell command that must succeed for the run to start, e.g.
#                 "nm -D /usr/local/bin/foo | grep -q new_symbol" for a fixed
#                 build, and for the control
#                 "test -x /usr/local/bin/foo && ! nm -D /usr/local/bin/foo | grep -q new_symbol"
# A package that is not installed or a file that does not exist is a mismatch.
[ $# -ge 2 ] || { echo "usage: $0 <tag> <harness.sh> [VAR=VALUE ...]" >&2; exit 64; }
T=$1; H=$2; shift 2
K=$HOME/keep/$T
if [ -e "$K" ]; then
	echo "$K exists: use a new tag" >&2
	exit 64
fi
mkdir -p "$K"
for a in "$@"; do
	case $a in
	[A-Za-z_]*=*) export "$a" ;;
	*) echo "not VAR=VALUE: $a" > "$K/ident.txt"; echo USAGE > "$K/done"; exit 64 ;;
	esac
done
export GUI_OUT=$K/out
bad=
{
	echo "== $(date) tag=$T harness=$H args: $*"
	uname -a
	[ -f "$H" ] || { echo "no harness $H"; bad=1; }
	for p in $IDENT_PKGS; do
		pkg query '%n-%v repo=%R installed=%t' "$p" || { echo "package $p not installed"; bad=1; }
	done
	for f in $IDENT_FILES; do
		sha256 "$f" || bad=1
	done
	echo "IDENT_CHECK: ${IDENT_CHECK:-none}"
	if [ -n "$IDENT_CHECK" ] && ! sh -c "$IDENT_CHECK"; then
		echo "IDENT_CHECK failed"; bad=1
	fi
	[ -z "$bad" ] || echo "IDENT MISMATCH"
	[ -z "$bad" ]
} > "$K/ident.txt" 2>&1 || { echo MISMATCH > "$K/done"; exit 1; }
sh "$H" > "$K/harness.log" 2>&1
rc=$?
grep -E 'RESULT|SUMMARY|TIMEOUT|classification|STOP_ON_FAIL' "$K/harness.log" > "$K/summary.txt"
echo "done rc=$rc" > "$K/done"
