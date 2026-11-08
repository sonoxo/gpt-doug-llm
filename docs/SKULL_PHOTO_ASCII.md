# SKULL-LLM: photographic anatomical ASCII (macOS)

The prior terminal command failed because the working folder
`~/gpt-doug-max` and manually downloaded
`~/Downloads/skull_ascii_ultra.py` did **not exist**. Installing Pillow
succeeded; the missing source file was the blocker.

## One-command launch from any Mac terminal directory

The source is hosted directly in `sonoxo/gpt-doug-llm`; no prior clone,
`cd`, manual Python file download, or named reference image is required.
**Pillow is required** (already installed in the user's observed terminal).

```bash
curl -fL --retry 2 \
  https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/scripts/skull_ascii_ultra.py \
  -o "$HOME/skull_ascii_ultra.py" &&
python3 "$HOME/skull_ascii_ultra.py" --demo \
  --width 95 --aspect 0.42 --color bone \
  --contrast 1.35 --gamma 0.80 \
  --save "$HOME/Desktop/SKULL-ANATOMICAL.txt"
```

The `--demo` option **explicitly authorizes** a one-time download of
a real photographed human skull from Wikimedia Commons, crops away the
lower photographic reflection, converts the anatomical tonal image to
copyable ASCII, and caches the PNG locally. Subsequent demo runs reuse
the cache. The source does not contain proprietary LLM tokens or access
the OpenAI service.

Reference attribution: **Xerto (Cyril NOVEL), "Skullfront.png",
Wikimedia Commons, CC BY-SA 3.0**,
https://commons.wikimedia.org/wiki/File:Skullfront.png.
The generated text file includes this attribution; redistributed
adaptations must follow the source image's CC BY-SA terms.

To convert any photo you have already saved, no network needed:

```bash
python3 "$HOME/skull_ascii_ultra.py" "$HOME/Pictures/my-skull.png" \
  --width 130 --style dense --color amber \
  --save "$HOME/Desktop/skull-photo.txt"
```

The software preserves the photo's existing contours, dark orbital
cavities, nasal aperture, zygomatic bones and teeth. Unlike
`gpt-doug skull live`, this is a **static 2D image-to-ASCII transform**
and does not claim to reconstruct a medically precise anatomical 3D
model or access a CL1 biochip.

### Offline validation

```bash
python3 -m pip install Pillow
python3 -m unittest tests.test_skull_photo_ascii -v
```

The tests generate synthetic test skull-like images in memory and mock
the demo downloader, so CI does not depend on Wikimedia availability.
