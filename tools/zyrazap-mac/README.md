# zyraZap for Mac — MVP

zyraZap packages the Mac cleanup workflow into a Chrome extension plus a local macOS Native Messaging helper.

## Museum role

zyraZap is a XUNIA/ZYRA utility exhibit for local developer-workstation hygiene. It scans only an explicit allowlist of known cache/log locations, defaults to dry-run, and uses backup → verify → delete for data that should be preserved before reclaiming disk space.

## Why there is a helper
Chrome extensions cannot directly scan arbitrary folders in a Mac home directory or delete local files. The helper is the minimal bridge. It accepts only a fixed allowlist of cleanup operations; it does not accept arbitrary shell commands.

## Current cleanup targets
- ZYRA SITL logs
- Hugging Face model cache
- Claude VM bundles
- Claude caches
- Cursor caches
- Codex runtime cache

Backup-required targets are copied with `rsync`, then checked with a second `rsync -ani --delete` pass. If verification fails, zyraZap does not delete the source.

## Install
1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select the `extension` folder in this package
5. Copy the generated extension ID shown by Chrome
6. In Terminal, from this package:
   ```bash
   ./native-host/install_native_host.sh YOUR_EXTENSION_ID
   ```
7. Restart Chrome
8. Open zyraZap and run **Scan Mac**
9. Keep **Dry run** enabled for the first pass
10. Default backup target is `/Volumes/Elements/ZyraZap-Backup`

## Safety design
- allowlist-only cleanup
- no arbitrary command execution
- dry-run default
- backups for important large data
- verification before deletion
- refuses to delete outside the current user's home directory
- does not touch Chrome profile folders, documents, photos, credentials, or arbitrary Application Support data

## Development note
For production distribution, package/sign/notarize the native helper and publish the Chrome extension with a stable extension ID.
