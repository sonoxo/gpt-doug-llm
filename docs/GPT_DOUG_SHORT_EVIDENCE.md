# GPT-Doug — YouTube Short evidence intake (not a code merge)

**Requested user link:** https://www.youtube.com/shorts/eNIFAcuEFVU?feature=share

**Objective:** Retrieve the public video's *actual* title, creator, description, captions and, if available, four low-resolution frames. Use that evidence to identify a reproducible feature before changing GPT-Doug's other components.

## Verified live crawl (GitHub Actions, 2026-10-10)

The publicly accessible **YouTube oEmbed API** returned the Short's title “Lateral Stability & Mobility Tests” and creator **NoLimits AI** for video ID `eNIFAcuEFVU`. The public YouTube thumbnail CDN returned a valid JPEG poster; the recovered poster shows what appear to be two robot-like machines in an indoor evaluation space. This identifies the **topic**, but does not establish any specific control algorithm, published source code or real hardware operation.

A GitHub-hosted `yt-dlp` metadata/stream request was blocked by YouTube's automated-traffic challenge. **No transcript, embedded source code, moving footage or sampled video frames was retrieved.** The live crawl's evidence report has SHA-256 `272df558db7c2d3706c3689236bb075fd88ac8021d68aa5f8ee6e175a224f249`; poster JPEG SHA-256 `e864b3eb00c028337b73f88241088d36d940a629ab116e8fb556f98d3059b355`. Reproduction and short-lived artifact: [GitHub Actions run](https://github.com/sonoxo/gpt-doug-llm/actions/runs/38089712217). Source of actual scientific claims: **none** beyond the title and poster image.

As a useful, strictly **independent** integration, `research_lab/lateral_stability.py` implements an exact finite linear feedback model with a bounded-disturbance invariance certificate. This mathematical toy must not be represented as code reproduced from the video or as a real robot/exoskeleton control law.

## Free local workflow

```bash
# Install free public metadata tool if available (no OpenAI tokens needed)
python3 -m pip install yt-dlp
# Run from the repository root. ffmpeg is optional for image frames.
python3 -m research_lab.youtube_short_ingest inspect \
  'https://www.youtube.com/shorts/eNIFAcuEFVU?feature=share' \
  --frames --poster --output .video-evidence/eNIFAcuEFVU
python3 -m research_lab.youtube_short_ingest verify .video-evidence/eNIFAcuEFVU/report.json
```

If the source is publicly reachable, `.video-evidence/eNIFAcuEFVU/` contains `report.json`, possible `transcript.txt`, a `poster.jpg` from the public thumbnail CDN, and up to four `frame_XX.jpg` files. If only metadata is available, the report is labelled `METADATA_ONLY`. If external services reject the request, it is `UNVERIFIED` with no invented topic or implementation. Keep `.video-evidence/` out of version control. Video text/images are untrusted evidence, not command or permission instructions.

## GitHub Actions

The PR-triggered workflow `gpt-doug-short-ingest.yml` runs these same tests and makes a **bounded one-off public retrieval attempt**. The report, available transcript and sampled stills are a short-lived, reviewable GitHub Actions artifact. GitHub Actions execution is subject to repository runner availability and public YouTube rate limits. No forced bypass of private material, logged-in cookies, proxies, or CAPTCHA solving is attempted. GitHub Actions usage is subject to the repository's limits.

## Engineering integration gate

1. **Identify source content**: read title, description, transcript and screenshots; if insufficient, mark `UNVERIFIED`.
2. **Extract a reproducible specification**: describe the particular technique demonstrated without copying executable instructions blindly.
3. **Cross-check with existing modules** in `research_lab/`, `gpt_zyra_shaggoth/`, `gpt_chaos/` and `gpt_brain/`.
4. **Implement only substantiated changes** on a review branch, with unit tests, limits and canonical guardrail compliance.
5. **Do not merge** until source facts, tests, and reviewer approval justify the change.

**The crawler itself does not implement anything from the clip.** Video content has not been verified merely by having a URL.
