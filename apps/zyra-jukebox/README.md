# ZYRA JUKEBOX

Free, source-aware, federated music and live-radio web player for the GPT-DOUG / ZYRA / XUNIA ecosystem.

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
