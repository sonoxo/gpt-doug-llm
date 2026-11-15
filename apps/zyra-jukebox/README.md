# ZYRA JUKEBOX

Free, source-aware, federated music and live-radio web player for the GPT-DOUG / ZYRA / XUNIA ecosystem.

## Safe Mac launch — avoids Git branch overwrite conflicts

If a prior CL1 checkout contains untracked `kraken_shield/` files, **do not** run `git clean -fd`, `git reset --hard`, or `git switch` to overwrite them. Keep the original checkout intact and clone MAX into a separate folder.

```bash
cd "$HOME" &&
if [ -d "$HOME/gpt-doug-max-jukebox/.git" ]; then
  git -C "$HOME/gpt-doug-max-jukebox" pull --ff-only
else
  git clone --depth 1 --single-branch \
    --branch feat/gpt-doug-max-glass-onion-egress-20261114 \
    https://github.com/sonoxo/gpt-doug-llm.git \
    "$HOME/gpt-doug-max-jukebox"
fi &&
cd "$HOME/gpt-doug-max-jukebox" &&
python3 -m http.server 8844 --bind 127.0.0.1 \
  --directory apps/zyra-jukebox
```

Open `http://127.0.0.1:8844/` on the same Mac. Leave that terminal open while browsing. A `127.0.0.1 refused to connect` browser message means this local HTTP server is not listening; it is not a paid-service failure. Use another terminal to verify with `curl -I http://127.0.0.1:8844/`.

The standalone static Jukebox on port 8844 does **not** automatically launch the CL1/Ollama backend on port 8787. The clone and server command do not erase or modify `~/gpt-doug-cl1` or external account data.

## v3 capabilities

- Windows 95 / Winamp-inspired interface
- RetroViz 95 psychedelic Trip Mode and multiple visualizer modes
- Full custom transport/controller deck: previous, rewind 10s, play/pause, stop, forward 10s, next, volume
- Media Session API hooks for compatible keyboards/headsets
- Persistent local queue and saved favorites
- Save current track/station, save session, export library JSON
- **Live Radio Directory** using the free/open Radio Browser API
- Radio search by station name/tag and optional country filter
- Top live stations view
- HTTPS stream filtering for browser-safe playback
- Internet Archive audio search and direct playback
- SoundCloud URL embedding
- YouTube URL embedding
- Local audio playback
- Federated launchers for SoundCloud, YouTube, Bandcamp, Audius, Jamendo, Internet Archive
- Source-aware queue and now-playing state

## Visualizer behavior

Direct/local audio can feed true Web Audio analysis when the browser permits it.

Live radio and embedded providers may not expose raw audio samples because of CORS/provider isolation. Those sources still trigger RetroViz using the linked ambient trip engine rather than pretending the page has raw beat data.

## Live-radio source

ZYRA JUKEBOX uses the community-maintained Radio Browser directory. Its station data is public-domain and its API is free/open. The player requests browser-safe HTTPS stations and preserves station/source metadata.

## Saved data

Favorites, queue, and the latest saved session are stored in the browser using `localStorage`. **EXPORT JSON** creates a portable user-owned library backup. No account or paid API is required.

## Design rule

ZYRA JUKEBOX does not scrape or rebroadcast restricted catalogs. Each result preserves its source and uses direct playback, provider embeds, public radio streams, or provider search links according to what the source permits.

## Ecosystem identity

- Product: ZYRA JUKEBOX
- Module: `zyra-jukebox`
- Visualizer: RetroViz 95
- Service role: Music Directory + Live Radio Federation
- Ontology class: MusicPlaybackGateway
