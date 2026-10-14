# GPT-Doug-MAX CoT XML: training preview and authorized UDP interop

## See an actual CoT marker in your browser immediately

```sh
cd ~/Downloads/gpt-doug-llm
bash scripts/doug-max cot show
```

`cot show` starts a loopback-only CoT UDP listener and the existing TAK-OS HTTP dashboard, sends a `LAB-VISIBLE-001` exercise medical event to the listener, **verifies receipt in the HTTP snapshot**, opens your default browser, and pans the map to the received marker. The example coordinates (34.6100, -86.5900) are operator-supplied training coordinates, **not** a verified medical incident. Nothing is sent to an external ATAK/iTAK device or TAK Server.

Keep the Terminal running. To open the browser manually, use the printed `OPEN THIS MAP: http://127.0.0.1:<random-port>/?cot=LAB-VISIBLE-001` URL. Ctrl+C shuts down the local listener and gateway. If you are running remotely or headless, use `bash scripts/doug-max cot show --no-open`; the local URL may require SSH forwarding to be accessible from another machine.

Use `--lat`, `--lon`, `--uid`, `--kind`, or `--callsign` to change the training event. No paid services, credentials, or external TAK access are needed.

`bash scripts/doug-max cot` now has three modes:

- `show`: open a local CoT map and verify one exercise event end to end.
- `preview`: generate CoT 2.0 XML with real UTC `time`, `start` and `stale` values. No socket is opened.
- `send`: send exactly **one** UDP datagram to a specified loopback or RFC1918 private IPv4 host, or to the approved one-hop exercise multicast group. Requires `--authorize`.

The sender is a **separate CLI**, not an extension of TAK-OS's isolated incoming loopback gateway or the browser demo. It supports only `LAB-`/`DEMO-` synthetic IDs, exercise `friendly` and `medical` types, and explicitly operator-entered coordinates. No target/hostile unit reports, sensor detections, remote automation, TAK Server credentials, control of equipment, or official TAK Server TLS broker protocol are implemented.

## Terminal commands (macOS and Linux, Python 3 standard library)

From the GPT-Doug repository root:

### Preview a non-operational exercise medical marker

```sh
bash scripts/doug-max cot preview --uid LAB-MED-001 --kind medical --lat 37.5407 --lon -77.4360 --callsign TRAINING-HLZ --remarks "Exercise only"
```

The output is an XML event with correctly expanded UTC timestamps, XML escaping, the supplied lat/lon, the CoT kind, and an explicit unverified-training disclaimer. Unknown altitude/accuracy use the CoT unknown sentinel `9999999.0`; the tool never fabricates meter-level accuracy.

### Send a training marker to your own ATAK/iTAK UDP listener on a private Wi-Fi LAN

```sh
bash scripts/doug-max cot send --uid LAB-MED-001 --kind medical --lat 37.5407 --lon -77.4360 --callsign TRAINING-HLZ --host 192.168.1.150 --port 4242 --authorize
```

Use the destination address and port your **own or explicitly authorized** client actually listens on. UDP sender success is **not** TAK client acknowledgment or proof of map display. A device may require networking, multicast permission, client port configuration, or a TAK Server; this command does not configure those.

### Send one exercise multicast marker (same local Wi-Fi segment)

```sh
bash scripts/doug-max cot send --uid LAB-GROUND-001 --kind friendly --lat 37.5407 --lon -77.4360 --callsign TRAINING-UNIT --multicast --authorize
```

Defaults: `239.2.3.1:6969`, multicast TTL **1** (one hop). If your Mac has multiple interfaces, add `--interface 192.168.1.20` with its **actual local Wi-Fi IPv4 address**. Network topology and TAK client settings determine whether a datagram will be seen.

### Verify using the existing GPT-Doug TAK-OS local gateway

In one terminal run the existing gateway with the **local-only legacy UDP adapter**, configured according to `docs/tak-os/README.md`. In a second terminal, transmit to its loopback listener:

```sh
bash scripts/doug-max cot send --uid LAB-LOCAL-001 --kind friendly --lat 37.5407 --lon -77.4360 --host 127.0.0.1 --port 6969 --authorize
```

A listening service must already be started. No network listener, TAK account, server, cloud service, or credential is silently installed by the sender.

## Input restrictions and operational boundaries

`--uid` must start `LAB-` or `DEMO-`. `--lat` and `--lon` are required and must be finite WGS84 coordinates. `--ttl` is 60-3600 seconds (default 180). `--kind` is `friendly` or `medical`, not a hostile classification. Callsigns and remarks are length- and XML-safety-checked. Destination must be a **numeric** IPv4 address; hostnames, public IPs, nonstandard multicast destinations, broadcasts and unapproved addresses fail closed.

The examples are fictional **training events** despite using illustrative real geographic coordinates. The message text always identifies the location as operator-entered, unverified, and exercise-only. Do not send fabricated actual positions or emergency reports to an operational network.

This tool does **not** establish a TLS session with TAK Server's certificate-protected interface (often port 8089). Direct UDP is neither mutual TLS nor an authenticated TAK broker connection. A real TAK Server integration requires a separate approved, certificate-validated connector and permissions.

## Validation

```sh
python3 -m unittest tests.test_tak_cot -v
bash -n scripts/doug-max
```

Tests verify UTC/stale calculations, escaped XML, compatibility with the existing lab gateway decoder, hard network boundaries, explicit authorization, a real local UDP socket send, one-hop multicast configuration (mocked: no broadcast), and the actual `doug-max cot preview` launcher. The suite does not send any packet to a third-party TAK installation.
