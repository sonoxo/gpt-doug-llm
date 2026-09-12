# Authorized Sensor Bridge

This integration is a fail-closed inventory and health layer for cameras, VMS gateways,
and other sensors the operator is explicitly authorized to access.

It intentionally does not perform network discovery, store credentials, capture video,
identify people, target entities, or autonomously task sensors.

Runtime inventory and health snapshots live under `~/.config/gpt-doug/` and are not
committed to Git.

## Commands

- `zyra-maven sensors add` - interactively register one exact approved host.
- `zyra-maven sensors validate` - validate authorization and allowlists.
- `zyra-maven sensors snapshot` - exact-host TCP health checks only.
- `zyra-maven sensors status` - show the latest local snapshot.

The integration manifest is packaged into the signed Maven release so deployments can
prove which connector policy shipped without publishing camera endpoints or credentials.
