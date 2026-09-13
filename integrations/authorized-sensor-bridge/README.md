# Authorized Sensor Bridge

This integration is a fail-closed inventory, health, and local command-center layer for cameras, VMS gateways, and other sensors the operator is explicitly authorized to access.

It intentionally does not perform network discovery, store credentials, identify people, target entities, or autonomously task sensors.

Runtime inventory and health snapshots live under `~/.config/gpt-doug/` and are not committed to Git.

## Commands

- `zyra-maven sensors add` - interactively register one exact approved network host.
- `zyra-maven sensors validate` - validate authorization and allowlists.
- `zyra-maven sensors snapshot` - exact-host TCP health checks only.
- `zyra-maven sensors status` - show the latest local snapshot.
- `zyra-maven hud` - open the loopback-only sensor command center.
- `zyra-maven hud --mode demo` - run synthetic nodes with interactive fault/recovery controls.
- `zyra-maven hud --mode live` - require a real authorized inventory and display its health telemetry.
- `scripts/zyra-local-camera setup` - register the local Mac camera as `LAPTOP-CAM-01` through a loopback-only hardware-health adapter.
- `scripts/zyra-local-camera status` - show local camera hardware/adapter health.
- `scripts/zyra-local-camera stop` - stop the local camera health adapter.
- `scripts/zyra-sensor-command-functional --mode live` - launch the functional HUD with optional browser-local camera preview.

Optional `latitude` and `longitude` fields can be stored with an authorized sensor to place it geospatially in the HUD. They are metadata only and do not change probe behavior.

The optional local preview is started explicitly by the operator in the browser using `getUserMedia`. Preview frames remain inside the browser tab: the ZYRA Python server does not record, store, upload, proxy, or analyze camera content.

The integration manifest is packaged into the signed Maven release so deployments can prove which connector policy shipped without publishing camera endpoints or credentials.
