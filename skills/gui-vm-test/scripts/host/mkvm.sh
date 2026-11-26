#!/bin/sh
# Create a vm-bhyve guest from an official FreeBSD VM image (UFS, raw or
# raw.xz) and prepare it with prep-image.sh.  Uses sudo for vm, dd,
# mdconfig, mount and the prepare step, and only touches the new guest.
#
# usage: mkvm.sh <name> <image.raw[.xz]> <ip/prefixlen> <gateway> <switch> <pubkey-file>
# env:   CPU (4)  MEM (4G)  DISK (20G)  NAMESERVER (none)
set -e -o pipefail
[ $# -eq 6 ] || { echo "usage: $0 <name> <image.raw[.xz]> <ip/prefixlen> <gateway> <switch> <pubkey-file>" >&2; exit 64; }
NAME=$1; IMG=$2; IP=$3; GW=$4; SW=$5; KEY=$6
CPU=${CPU:-4}; MEM=${MEM:-4G}; DISK=${DISK:-20G}
HERE=$(cd "$(dirname "$0")" && pwd)

[ -r "$IMG" ] || { echo "cannot read image $IMG" >&2; exit 1; }
[ -f "$KEY" ] || { echo "no public key $KEY" >&2; exit 1; }
case $IMG in
*.xz) xz -t "$IMG" || { echo "$IMG is damaged" >&2; exit 1; } ;;
esac

vmdir=$(sysrc -n vm_dir)
case $vmdir in
zfs:*) vmdir=$(zfs get -H -o value mountpoint "${vmdir#zfs:}") ;;
esac
[ -d "$vmdir" ] || { echo "cannot find vm_dir" >&2; exit 1; }
if sudo vm list | awk 'NR > 1 { print $1 }' | grep -qx "$NAME"; then
	echo "guest $NAME already exists" >&2; exit 1
fi
sudo vm switch list | awk 'NR > 1 { print $1 }' | grep -qx "$SW" ||
    { echo "no switch $SW" >&2; exit 1; }

sudo vm create -s "$DISK" -c "$CPU" -m "$MEM" "$NAME"
G=$vmdir/$NAME
md=
ok=
cleanup() {
	set +e
	sudo umount "$G/mnt" 2>/dev/null
	[ -z "$md" ] || sudo mdconfig -d -u "$md"
	sudo rmdir "$G/mnt" 2>/dev/null
	[ -n "$ok" ] || echo "FAILED; remove the half-made guest with: sudo vm destroy -f $NAME" >&2
}
trap cleanup EXIT
trap 'exit 1' INT TERM HUP
case $IMG in
*.xz) unxz -c "$IMG" | sudo dd of="$G/disk0.img" bs=1m conv=sparse,notrunc status=none ;;
*) sudo dd if="$IMG" of="$G/disk0.img" bs=1m conv=sparse,notrunc status=none ;;
esac
# The file keeps the size vm create gave it; fix the backup GPT, growfs
# extends the root file system on first boot.
md=$(sudo mdconfig -a -t vnode -f "$G/disk0.img")
sudo gpart recover "$md"
part=$(gpart show -p "$md" | awk '$4 == "freebsd-ufs" { print $3 }')
[ -n "$part" ] || { echo "no freebsd-ufs partition in $IMG (use the -ufs image)" >&2; exit 1; }
sudo mkdir "$G/mnt"
sudo mount "/dev/$part" "$G/mnt"
sudo sh "$HERE/prep-image.sh" "$G/mnt" "$NAME" "$IP" "$GW" "$KEY" $NAMESERVER
sudo umount "$G/mnt"

sudo sysrc -f "$G/$NAME.conf" loader=uefi cpu="$CPU" memory="$MEM" \
    network0_type=virtio-net network0_switch="$SW" \
    disk0_type=virtio-blk disk0_name=disk0.img utctime=yes >/dev/null
ok=1
echo "created $NAME in $G; start it with: sudo vm start $NAME"
