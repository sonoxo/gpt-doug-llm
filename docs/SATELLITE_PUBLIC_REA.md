# GPT-Doug / REA / public satellite catalog

Status: local implementation. No satellite network, uplink, spacecraft tasking, or remotely deployed replica is connected.

REA (https://github.com/morluto/rea) is a reverse-engineering CLI/MCP, **not** a satellite access tool. This module uses only its local `rea inspect-model-artifact` on operator-approved .gguf/.safetensors files. REA is optional and is never auto-installed.

The opt-in catalog reads a single fixed URL: `https://celestrak.org/NORAD/elements/gp.php?GROUP=STATIONS&FORMAT=JSON`. It strips records to name, NORAD catalog ID, and epoch with source hash and timestamp. No positions, orbit propagation, radios, commands, host scanning, or autonomous replication.

From the repository root:

```sh
python3 -m integrations.satellite_readonly status
python3 -m integrations.satellite_readonly catalog
python3 -m integrations.satellite_readonly catalog --live
python3 -m integrations.satellite_readonly catalog --fixture /path/to/stations.json
python3 -m integrations.satellite_readonly replica-plan --root /approved/models --artifact model.gguf
python3 -m integrations.satellite_readonly rea-model --root /approved/models --artifact model.gguf
python3 -m unittest discover -s tests -p 'test_satellite_readonly_bridge.py' -v
```

`replica-plan` only hashes an approved existing local model file and prints a reviewable manifest; it does not clone, copy, install or deploy code. Reproducing an AI service requires separate model licenses, weights, code, policy approval, and infrastructure. REA upstream lists Node.js ^22.19.0 || ^24.11.0 || >=26.0.0, and `rea-agents` 6.7.0 in the inspected package manifest. Review its release before locally installing. No paid reverse-engineering provider is required for the model metadata command.

Tests are offline and cannot prove live network availability or real REA runtime behavior. Public source timestamps must not be described as real-time spacecraft telemetry. This adapter is independent of the existing NASA/NOAA TAK-OS display and N2YO proxy.
