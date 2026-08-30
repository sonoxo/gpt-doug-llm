# NXYZ Mouse Mic Privacy Policy

Effective date: August 30, 2026

NXYZ Mouse Mic is a browser extension that provides voice and keyboard click guidance on Palantir Foundry pages that the user is already authorized to access.

## Data handling

NXYZ Mouse Mic does not operate a developer-controlled backend service and does not send webpage content, DOM labels, typed commands, click targets, or browsing activity to the developer.

The extension examines visible controls on the active supported webpage inside the browser in order to locate, highlight, describe, and, when requested, activate a matching control. Typed commands are processed in the browser.

Optional voice recognition uses the speech-recognition implementation exposed by the user's browser. Depending on the browser and operating environment, speech recognition may be processed by the browser vendor or another service selected by the browser. NXYZ Mouse Mic does not transmit microphone audio to a developer-operated server and does not receive or retain microphone recordings on a developer-operated server.

Speech synthesis is provided by the browser or operating system.

## Collection and retention

NXYZ Mouse Mic does not intentionally collect or retain personal information on developer-operated infrastructure. The extension does not include advertising, analytics, tracking pixels, or a developer-operated telemetry service.

The current extension does not request Chrome's `storage` permission and does not persist command history through Chrome extension storage.

## Permissions

- `activeTab`: used when the user invokes NXYZ Mouse Mic so the extension can interact with the active supported page.
- `scripting`: used to connect the Mouse Mic content script and styles to the active supported page when necessary.
- `https://*.palantirfoundry.com/*`: limits the extension's webpage access to Palantir Foundry enrollments rather than requesting access to all websites.

## High-impact actions

NXYZ Mouse Mic includes an additional confirmation step for controls whose labels indicate potentially significant actions such as delete, deploy, publish, approve, submit, revoke, or permission changes. This safeguard does not replace the authorization, permissions, confirmation dialogs, or security controls of the website being used.

## Sale or transfer of data

NXYZ Mouse Mic does not sell user data. The extension does not use user data for advertising, creditworthiness, lending, or unrelated profiling.

## Third-party services and trademarks

NXYZ Mouse Mic is an independent extension and is not affiliated with, sponsored by, or endorsed by Palantir Technologies Inc. Palantir and Foundry are referenced only to describe compatibility with the supported website.

Users remain subject to the privacy policies and terms of the websites and browser services they use.

## Contact

Questions or privacy requests can be submitted through the project's public GitHub issue tracker:

https://github.com/sonoxo/gpt-doug-llm/issues
