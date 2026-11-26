#!/bin/sh
# Prepare a mounted FreeBSD VM image so that it boots straight into a state
# where the host can ssh in as root with a throwaway key.
#
# usage: prep-image.sh <mountpoint> <hostname> <ip/prefixlen> <gateway> <pubkey-file> [nameserver]
#
# Run as root, on the root file system of an image attached with mdconfig
# and mounted; anything else is refused.
set -e
[ $# -ge 5 ] || { echo "usage: $0 <mountpoint> <hostname> <ip/prefixlen> <gateway> <pubkey-file> [nameserver]" >&2; exit 64; }
M=$1; H=$2; IP=$3; GW=$4; KEY=$5; NS=$6
M=$(realpath "$M")
[ "$M" != / ] || { echo "refusing to modify /" >&2; exit 1; }
# Only a file system mounted from a memory disk (an image), never a live
# root or a jail.
mount -p | awk -v m="$M" '$2 == m && $1 ~ "^/dev/md[0-9]" { f = 1 } END { exit !f }' ||
    { echo "$M is not a mounted md(4) image" >&2; exit 1; }
[ -f "$M/etc/rc.conf" ] || [ -d "$M/etc/rc.d" ] || { echo "$M does not look like a FreeBSD root" >&2; exit 1; }
[ -f "$KEY" ] || { echo "no public key $KEY" >&2; exit 1; }

touch "$M/etc/rc.conf"
sed -i '' -e '/^hostname=/d' -e '/^ifconfig_DEFAULT=/d' -e '/^ifconfig_vtnet0/d' \
    -e '/^defaultrouter=/d' "$M/etc/rc.conf"
cat >> "$M/etc/rc.conf" <<EOR
hostname="$H"
ifconfig_vtnet0="inet $IP"
defaultrouter="$GW"
growfs_enable="YES"
sshd_enable="YES"
sendmail_enable="NONE"
EOR
[ -z "$NS" ] || echo "nameserver $NS" > "$M/etc/resolv.conf"
mkdir -p -m 700 "$M/root/.ssh"
cp "$KEY" "$M/root/.ssh/authorized_keys"
chmod 600 "$M/root/.ssh/authorized_keys"
echo 'PermitRootLogin prohibit-password' >> "$M/etc/ssh/sshd_config"
# Serial console, so `vm console` shows the boot if ssh never comes up.
printf 'console="comconsole"\nautoboot_delay="2"\n' >> "$M/boot/loader.conf"
echo "prepared $M: $H $IP gw $GW"
