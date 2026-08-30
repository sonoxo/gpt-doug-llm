# NXYZ Mouse Mic — Accessibility Design Notes

NXYZ Mouse Mic is an **accessibility-supporting browser tool** designed to reduce pointer-precision and visual-search demands when navigating authorized Palantir Foundry pages.

It is intended to support users who benefit from alternate input, spoken guidance, visible highlighting, large target labels, and confirmation before significant actions.

## Important compliance statement

NXYZ Mouse Mic is **not represented as an ADA certification, WCAG conformance certification, accessibility audit, or legal compliance guarantee**.

ADA compliance is evaluated in context and depends on the complete product/service experience, including the underlying third-party application, browser, operating system, assistive technology, organizational policies, content, and user workflows. Installing this extension does not make another application legally compliant.

The project uses WCAG-oriented engineering practices as a design reference and should undergo independent accessibility testing before any formal conformance claim is made.

## Accessibility goals

| User need | Mouse Mic behavior | Current state |
| --- | --- | --- |
| Reduce precise mouse movement | Find controls by accessible label or visible text and activate by command | Implemented |
| Reduce visual-search load | Highlight the best target and optionally number all visible controls | Implemented |
| Provide a non-speech path | Typed commands in the extension popup | Implemented |
| Provide spoken guidance | Browser speech synthesis announces target/location/status | Implemented; browser dependent |
| Support reduced motion | Documentation SVG animation stops under `prefers-reduced-motion: reduce` | Implemented for repo visuals |
| Reduce accidental significant actions | High-impact text patterns require `confirm click` | Implemented |
| Preserve application authorization | Extension operates inside the user's existing Foundry permissions | Implemented by design |
| Screen-reader interoperability | Accessible-name discovery is used, but end-to-end AT interoperability needs testing | Audit required |
| Full keyboard-only operation | Popup supports keyboard entry; full workflow should be independently audited | Audit required |
| Color/contrast conformance | High-contrast visual design is intentional; formal contrast measurements are still required | Audit required |

## WCAG-oriented engineering map

These are **design targets and implementation references, not conformance claims**.

- **Keyboard access:** typed command fallback reduces dependence on speech and pointer input.
- **Focus and target visibility:** selected controls receive a high-contrast visual outline and scroll into view.
- **Multiple ways to identify controls:** Mouse Mic can use accessible labels, titles, visible text, placeholders, names, IDs, and numbered targets.
- **Status communication:** the overlay provides visible status and browser speech synthesis can provide audible status.
- **Motion sensitivity:** repository visual assets honor the user's reduced-motion preference.
- **Error prevention / significant actions:** potentially consequential controls are held pending explicit confirmation.
- **Name/role/value awareness:** target discovery reads semantic browser attributes such as `aria-label`, role-bearing elements, and native interactive elements.

## Assistive interaction paths

### Voice-guided

`Speak request → discover controls → match target → highlight → speak location → click or confirm`

### Keyboard-guided

`Type request → discover controls → match target → highlight → visible status → click or confirm`

### Numbered-target mode

`show targets → visible numbered overlays → click number N → safety check → execute or confirm`

## What Mouse Mic does not do

- It does not bypass authentication, authorization, tenant policy, or application approvals.
- It does not guarantee that a third-party page is accessible.
- It does not replace a screen reader, switch-control system, browser zoom, OS accessibility features, or professional accessibility remediation.
- It does not certify ADA, Section 508, EN 301 549, or WCAG conformance.

## Pre-release accessibility audit checklist

Before making a formal accessibility or compliance statement, test at minimum:

- keyboard-only operation;
- screen reader behavior with VoiceOver, NVDA, and/or JAWS as applicable;
- browser zoom at 200% and 400%;
- text spacing and reflow;
- contrast for popup, overlay, numbered badges, focus/highlight state, and status messages;
- reduced-motion behavior;
- speech-recognition failure/fallback behavior;
- target-name accuracy with ARIA and native HTML controls;
- high-impact confirmation using keyboard and voice;
- error messages and recovery paths;
- Foundry UI changes across supported tenant versions.

## Product principle

> **Reduce interaction friction without reducing user control.**

Accessibility support is part of the NXYZ product architecture, not a cosmetic layer. The preferred interaction model is multimodal, visible, reversible where possible, and explicit at consequential boundaries.
