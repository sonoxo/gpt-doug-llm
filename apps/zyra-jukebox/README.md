# ZYRA JUKEBOX

Free, source-aware, federated music web player for the GPT-DOUG / ZYRA / XUNIA ecosystem.

## v1 capabilities
- Windows 95 / Winamp-inspired interface
- Internet Archive audio search and direct playback
- SoundCloud URL embedding
- YouTube URL embedding
- Local audio playback
- Federated directory launchers for SoundCloud, YouTube, Bandcamp, Audius, Jamendo, and Internet Archive
- Queue and now-playing state
- RetroViz 95 audio-reactive spectrum, oscilloscope, and binary modes for direct/local audio

## Design rule
ZYRA JUKEBOX does not scrape or rebroadcast restricted catalogs. Each result preserves its source and uses direct playback, provider embeds, or provider search links according to what the source permits.

## Run locally
Serve this directory with any static web server and open `index.html` through that server. Browser security policies may block Web Audio analysis from some cross-origin streams; provider embeds remain playable but are not fed into RetroViz unless the provider exposes audio to the page.

## Ecosystem identity
- Product: ZYRA JUKEBOX
- Module: `zyra-jukebox`
- Visualizer: RetroViz 95
- Service role: Music Directory Federation
- Ontology class: MusicPlaybackGateway
