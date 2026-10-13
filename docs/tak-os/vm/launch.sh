#!/bin/sh
# Local Ubuntu VM starter, explicitly invoked by the operator.
# Does not install Ubuntu or download ISO automatically.
set -eu
ISO="${1:-}"
DISK="${TAK_VM_DISK:-tak-os-ubuntu.qcow2}"
CPU="${TAK_VM_CPUS:-2}"
RAM="${TAK_VM_RAM_MB:-4096}"
DISK_GB="${TAK_VM_DISK_GB:-20}"
SSH_PORT="${TAK_VM_SSH_PORT:-2222}"
if [ -z "$ISO" ] || [ ! -f "$ISO" ]; then
  printf 'Usage: %s /absolute/path/to/ubuntu-server.iso\n' "$0" >&2
  echo 'Provide your own official Ubuntu ISO. No download or cloud VM is performed.' >&2
  exit 2
fi
command -v qemu-system-x86_64 >/dev/null || { echo 'qemu-system-x86_64 not installed' >&2; exit 1; }
command -v qemu-img >/dev/null || { echo 'qemu-img not installed' >&2; exit 1; }
for NUM in "$CPU" "$RAM" "$DISK_GB" "$SSH_PORT"; do
  case "$NUM" in ''|*[!0-9]*) echo 'VM numbers must be positive integers' >&2; exit 2 ;; esac
done
if [ "$CPU" -lt 1 ] || [ "$CPU" -gt 32 ] || [ "$RAM" -lt 1024 ] || [ "$RAM" -gt 131072 ] || [ "$DISK_GB" -lt 20 ] || [ "$DISK_GB" -gt 2000 ] || [ "$SSH_PORT" -lt 1024 ] || [ "$SSH_PORT" -gt 65535 ]; then
 echo 'VM input exceeds supported demo bounds' >&2; exit 2
fi
case "$DISK" in *..*|/*) echo 'TAK_VM_DISK must be a relative, non-traversing filename' >&2; exit 2 ;; esac
if [ ! -f "$DISK" ]; then
  echo "Creating new $DISK ($DISK_GB GB virtual size)"
  qemu-img create -f qcow2 "$DISK" "${DISK_GB}G"
fi
if [ -e /dev/kvm ] && [ -r /dev/kvm ]; then ACCEL=kvm
elif [ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = x86_64 ]; then ACCEL=hvf
else ACCEL=tcg
fi
printf 'Booting isolated local VM; SSH host port 127.0.0.1:%s -> guest 22.\n' "$SSH_PORT"
printf 'Install Ubuntu OpenSSH server in guest. Then host tunnel: ssh -p %s -N -L 8080:127.0.0.1:8080 USER@127.0.0.1\n' "$SSH_PORT"
exec qemu-system-x86_64 -accel "$ACCEL" -smp "$CPU" -m "$RAM" \
  -drive "file=$DISK,if=virtio,format=qcow2" \
  -cdrom "$ISO" -boot once=d \
  -nic "user,hostfwd=tcp:127.0.0.1:${SSH_PORT}-:22"
