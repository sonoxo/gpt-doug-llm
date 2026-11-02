#!/usr/bin/env python3
"""Glass Onion acoustic evidence: turn a local WAV recording into a spectrogram.

Dependencies: numpy, matplotlib. Supported input: uncompressed PCM WAV.
This makes sound visible; it cannot identify source-code repositories by itself.
"""
import argparse
import hashlib
import json
import wave
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("audio", type=Path)
    p.add_argument("--output", type=Path, default=Path("glass-onion-sounds.png"))
    args = p.parse_args()
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    with wave.open(str(args.audio), "rb") as wav:
        channels, rate, width, count = wav.getnchannels(), wav.getframerate(), wav.getsampwidth(), wav.getnframes()
        if width != 2:
            p.error("Use a signed 16-bit PCM WAV (ffmpeg -i input.mp4 -vn -ac 1 -c:a pcm_s16le audio.wav)")
        samples = np.frombuffer(wav.readframes(count), dtype="<i2").astype(np.float32).reshape(-1, channels).mean(axis=1) / 32768
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.specgram(samples, NFFT=1024, Fs=rate, noverlap=768, cmap="magma")
    ax.set(title="GLASS ONION // SOUND SPECTROGRAM", xlabel="Time (seconds)", ylabel="Frequency (Hz)")
    fig.tight_layout()
    fig.savefig(args.output, dpi=150)
    plt.close(fig)
    report = {"input_sha256": hashlib.sha256(args.audio.read_bytes()).hexdigest(),
              "sample_rate": rate, "channels": channels, "duration_seconds": round(len(samples)/rate, 3),
              "spectrogram": str(args.output), "source_repositories_identified": []}
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
