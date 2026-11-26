#!/bin/sh
# ssh/scp to a test guest as root with the throwaway key.
#
# usage: GUI_TEST_KEY=<private key> gssh.sh <ip> [command...]
#        GUI_TEST_KEY=<private key> gssh.sh -c <scp-args...>    (remote side: root@<ip>:path)
# The host key is not recorded: guests are rebuilt and get new keys.
: "${GUI_TEST_KEY:?set GUI_TEST_KEY to the private key}"
if [ "$1" = -c ]; then
	shift
	exec scp -q -i "$GUI_TEST_KEY" -o StrictHostKeyChecking=no \
	    -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=5 \
	    -o BatchMode=yes -o IdentitiesOnly=yes "$@"
fi
ip=${1:?usage: gssh.sh <ip> [command...]}; shift
exec ssh -i "$GUI_TEST_KEY" -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=5 \
    -o BatchMode=yes -o IdentitiesOnly=yes -o ServerAliveInterval=30 "root@$ip" "$@"
