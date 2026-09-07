# ZYRA JUKEBOX

Free, source-aware, federated music web player for the GPT-DOUG / ZYRA / XUNIA ecosystem.

## v2 capabilities — RetroViz 95 Trip Mode
- Windows 95 / Winamp-inspired interface
- Internet Archive audio search and direct playback
- SoundCloud URL embedding with widget play/pause event linkage
- YouTube URL embedding with iframe play/pause event linkage
- Local audio playback
- Federated directory launchers for SoundCloud, YouTube, Bandcamp, Audius, Jamendo, and Internet Archive
- Queue and now-playing state
- Automatic `TRIP MODE` whenever supported direct/local audio starts
- True Web Audio analysis for direct/local audio
- Linked ambient visual fallback for embedded SoundCloud and YouTube playback
- Full-screen psychedelic visual stage
- Visual modes: Trip Mode, Neon Tunnel, Kaleidoscope, Liquid Plasma, Cosmic Drift, Binary Rain, Spectrum Bars, Oscilloscope
- Reduced-motion awareness

## Visual behavior
Direct and local audio that can be connected to the browser Web Audio API drives RetroViz using live bass, mid, treble, waveform, and overall-energy measurements. Embedded SoundCloud and YouTube players remain source-isolated by browser/provider security boundaries, so ZYRA JUKEBOX listens for player play/pause events and runs the linked ambient trip engine while those embeds are playing. The UI labels the difference rather than pretending embedded audio is being sampled.

## Design rule
ZYRA JUKEBOX does not scrape or rebroadcast restricted catalogs. Each result preserves its source and uses direct playback, provider embeds, or provider search links according to what the source permits.

## Run locally
Serve this directory with any static web server and open `index.html` through that server. Browser security policies may block Web Audio analysis from some cross-origin direct streams; provider embeds remain playable and still receive linked ambient Trip Mode through their public widget/iframe events.

## Ecosystem identity
- Product: ZYRA JUKEBOX
- Module: `zyra-jukebox`
- Visualizer: RetroViz 95
- Visual engine: RetroViz 95 Trip Mode
- Service role: Music Directory Federation
- Ontology class: MusicPlaybackGateway
