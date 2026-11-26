#!/bin/sh
# Install the test tools and the packages under test in a fresh guest.
#
# usage: guest-setup.sh [-r <local-repo-url>] [-l <pkg>] [-o <pkg>] [-f <file.pkg>] ...
#   -r URL    pkg repository served by the host (a poudriere repository with
#             its catalogue); registered as "local" with priority 100
#   -l PKG    install PKG from the local repository (needs -r)
#   -o PKG    install PKG from the configured (official) repositories
#   -f FILE   install a package file already copied to the guest (replacing
#             an installed package of the same name); its dependencies come
#             from the configured repositories
# Every option takes one argument and may be repeated; they are processed
# in order.  Set HTTP_PROXY/HTTPS_PROXY in the
# environment when the guest has no direct route to the Internet.
set -e
export ASSUME_ALWAYS_YES=yes
TOOLS="xorg-vfbserver xdotool xprop xwininfo xwd xdpyinfo gdb dbus dejavu"

pkg -N >/dev/null 2>&1 || pkg bootstrap -y
pkg update
pkg install -y $TOOLS

while getopts r:l:o:f: o; do
	case $o in
	r)
		mkdir -p /usr/local/etc/pkg/repos
		cat > /usr/local/etc/pkg/repos/local.conf <<EOR
local: { url: "$OPTARG", signature_type: "none", priority: 100, enabled: yes }
EOR
		pkg update -f
		;;
	l) pkg install -y -r local "$OPTARG" ;;
	o) pkg install -y "$OPTARG" ;;
	f)
		# pkg add only finds dependencies next to the file, so install
		# the missing ones from the repositories first.
		for d in $(pkg query -F "$OPTARG" '%dn'); do
			pkg info -e "$d" || pkg install -y "$d"
		done
		pkg add -f "$OPTARG"
		;;
	*) exit 64 ;;
	esac
done
shift $((OPTIND - 1))
[ $# -eq 0 ] || { echo "unexpected argument: $1 (one package per option)" >&2; exit 64; }
pkg check -d -a
echo SETUP-OK
