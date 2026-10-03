# XUNIA ZYRA Chaotic Good Gateway

Chrome Manifest V3 browser shield and local capability layer for the XUNIA / ZYRA / GPT-Doug workflow.

## Scope

This protects the browser control surface it actually owns: supported Palantir Foundry tabs, GitHub, and localhost development apps. It does not claim to protect or control the entire internet or third-party infrastructure.

## Capabilities

- local 2-second page-state loop
- sanitized page snapshots
- local security scan for HTTP/password hazards, HTTPS-to-HTTP forms, cross-origin forms, punycode hosts, mixed-content references, and visible `javascript:` links
- fixed host allowlist
- default read-first mode
- five-minute temporary write arming for programmatic click/type
- automatic disarm on navigation
- shield enforcement for programmatic form/navigation hazards
- password, file, and hidden-field typing blocked
- local action audit log without typed text
- panic stop that stops the loop and disarms writes
- no remote command server and no extension network exfiltration

## Install

1. Unzip the package.
2. Open `chrome://extensions`.
3. Enable Developer mode.
4. Click Load unpacked.
5. Select the `xunia-zyra-chaotic-good-gateway` folder.
6. Reload Foundry/GitHub tabs that were already open.
7. Open the extension and run Shield scan.
8. Keep writes disarmed unless you intentionally want the popup to click/type.

## Write gate

`highlight`, `focus`, `scroll`, scans, and snapshots are read-first operations. `click` and `type` require a temporary arm window of at most five minutes. Navigation automatically disarms the write gate.
