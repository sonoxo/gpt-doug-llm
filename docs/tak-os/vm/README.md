# Free local Ubuntu VM — GPT-Doug TAK-OS
No paid hosted VM required. This is a local **simulator**, not official TAK Server.

## Linux x86_64

1. Install `qemu-system-x86`, `qemu-utils`, and an Ubuntu Server ISO (official Canonical website).
2. Copy `docs/tak-os` into a local directory. Run from a dedicated VM directory:
   ```sh
   cd docs/tak-os/vm
   sh launch.sh /absolute/path/to/ubuntu-24.04-live-server-amd64.iso
   ```
3. Install Ubuntu using the graphical QEMU console. Enable **OpenSSH server** during installation.
4. Copy `docs/tak-os` into the guest using an SSH/SCP transfer. Run **inside Ubuntu guest**:
   ```sh
   cd tak-os
   sh start.sh web
   ```
5. On host, forward authenticated SSH; the VM guest web service stays bound to its loopback:
   ```sh
   ssh -p 2222 -N -L 8080:127.0.0.1:8080 YOUR_GUEST_USER@127.0.0.1
   ```
6. Open http://127.0.0.1:8080 **on the host**. An explicit login and host-key verification are required.

Important: QEMU `hostfwd=...:8080` alone would **not** reach a service bound to guest 127.0.0.1. Only port 22 is forwarded; the SSH tunnel is the intended secure access path.

On macOS Apple Silicon, the free UTM direct download is usually simpler than x86_64 QEMU software emulation. Select an Ubuntu ARM64 ISO and use UTM port forwarding/SSH as documented by UTM. Free VM resources still require local CPU, RAM, and disk space.

## Safety and status
- `launch.sh` only creates a disk image if missing; never overwrites an existing VM disk.
- No ISO download, credentials, privileged host changes, or remote deployments.
- This browser demo does not run a live TAK server or bridge into operational CoT networks.
- Use local trusted user access; do not expose HTTP 8080 directly to the Internet.
