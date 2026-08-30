# NXYZ Mouse Mic — Chrome Web Store Publish Checklist

Package version: **1.0.2**

## Before upload

- [x] Manifest V3
- [x] Version bumped to 1.0.2
- [x] Unused `storage` permission removed
- [x] Access limited to `https://*.palantirfoundry.com/*`
- [x] 16×16 icon
- [x] 48×48 icon
- [x] 128×128 icon
- [x] Privacy policy
- [x] Store listing copy
- [x] Reviewer test instructions
- [x] GitHub Actions packaging workflow
- [x] High-impact click confirmation remains enabled
- [x] No paid API key or developer-operated backend required

## Developer Dashboard

1. Open the Chrome Web Store Developer Dashboard.
2. Choose **Add new item**.
3. Upload the ZIP produced by the `NXYZ Mouse Mic Store Package` GitHub Actions workflow.
4. In **Store listing**, use the text in `STORE-LISTING.md`.
5. Category: **Accessibility**.
6. Upload the 128×128 store icon and at least one 1280×800 or 640×400 product screenshot.
7. Add a 440×280 promo tile if desired.
8. Homepage/source: `https://github.com/sonoxo/gpt-doug-llm/tree/main/tools/nxyz-mouse-mic`.
9. Support URL: `https://github.com/sonoxo/gpt-doug-llm/issues`.
10. Privacy policy URL: `https://github.com/sonoxo/gpt-doug-llm/blob/main/tools/nxyz-mouse-mic/PRIVACY.md`.
11. In **Privacy**, use the permission and data-use explanations in `STORE-LISTING.md`.
12. Set initial visibility to **Unlisted** for the first review/install test.
13. Submit for review.
14. After approval and a successful clean install from the Store, change visibility to **Public** when ready.

## Required publisher-side items

These cannot be completed from the source repository:

- Chrome Web Store developer registration/payment, if not already completed.
- Google account 2-step verification.
- Developer Dashboard contact-email verification if requested.
- Final Store listing form entries and declarations.
- Uploading store screenshots/assets.
- Clicking **Submit for review**.

## Release test

After Chrome Web Store approval:

1. Remove the unpacked development copy from a clean Chrome profile.
2. Install the Store version.
3. Open an authorized Foundry page.
4. Run `show targets`.
5. Run `where is <visible control>`.
6. Run `click <normal control>`.
7. Verify a high-impact control asks for `confirm click`.
8. Verify the extension does not run on `chrome://` pages or unrelated sites.
