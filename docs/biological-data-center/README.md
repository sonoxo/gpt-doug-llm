# XUNIA Biological Data Center / CL1

**Public route (after Pages publish):** https://xunia.org/biological-data-center/

**Hosting:** existing free GitHub Pages for the static interface. No Vercel, no commercial inference API, no paid compute.

**Local CL1 URL:** http://127.0.0.1:8871/ when the user starts the included local Python server.

## What exists

A clickable 30-node, 43-relationship spatial software ontology. Nodes have biological analogies (nucleus, neural trunks, immune cells, genome, mitochondria) and honest source-status labels. These are **visual and architectural metaphors**, not living neural tissue, biosensors, medical devices, or physical CL1 hardware.

Public GitHub Pages displays architecture, animated synthetic signal flow, source provenance, layer filters, interactive inspection, full JSON export, and an optional dated public Sonoxo repository genome. Its public mode NEVER claims to show live Mac service status.

## Start localhost telemetry on Mac

Use a fresh checkout to avoid the previous untracked-file Git conflicts:

    cd "$HOME"
    git clone --depth 1 --single-branch \
      -b feat/xunia-cl1-biological-data-center-20261115 \
      https://github.com/sonoxo/gpt-doug-llm.git \
      "$HOME/xunia-bio-cl1"
    cd "$HOME/xunia-bio-cl1"
    bash scripts/xunia-bio --check
    bash scripts/xunia-bio

Open http://127.0.0.1:8871/ and leave the Terminal running. This does not start or modify Ollama, GPT-DOUG, Jukebox or CL1-AURA. Those services run separately.

The local server samples only a UTC timestamp, bounded TCP availability on 127.0.0.1 for configured services, approximate one-minute system load, logical CPU count, and free local disk. A TCP LISTENING state does not prove app identity or successful inference.

The server refuses off-host Host and Origin requests, blocks cross-site fetches, serves only a narrow set of static routes, denies mutation methods, and sends a restrictive Content Security Policy. No API keys, bank data, music payouts, credentials, prompt content, private vault material, or biosignals are exported. The website's synthetic animated pulses are **not measured biological data**.

## Ontology/evidence

The versioned source is docs/biological-data-center/ontology.json. A node tagged feature-branch is pending and is NOT proof of a merged deployed service. The repository genome is read-only from the existing dated docs/ecosystem-observatory/snapshot.json source; repository membership does not imply runtime integration.

## Mac startup and blank spatial field recovery

If Terminal prints `XUNIA CL1: localhost port in use`, an older process is still listening on port 8871. The launcher will **not** kill it or replace it. Find that specific earlier `Python scripts/xunia_bio_cl1.py` Terminal tab and press **Control+C** in that tab. If unsure, inspect it with `lsof -nP -iTCP:8871 -sTCP:LISTEN` and do not terminate other processes.

After stopping the earlier XUNIA server:

    cd ~/xunia-bio-cl1
    git pull --ff-only
    bash scripts/xunia-bio --check
    bash scripts/xunia-bio

Enter `http://127.0.0.1:8871/biological-data-center/` manually in Chrome and use **Command+Shift+R** to load the latest browser assets. Keep the server Terminal open.

A previous build showed background stars but no ontology nodes because a non-finite horizontal projection broke the browser Canvas gradient. The renderer now bounds the projected coordinates. Both Node's full-ontology Canvas harness and a **real headless Chrome** test must render 30 nodes/43 edges before CI can pass. The browser reports a rendering error visibly instead of silently drawing an empty canvas. Synthetic pulses remain visual metaphors, not real biological data.

## Validate

    python3 -m unittest discover -s tests -p 'test_xunia_biological_data_center.py' -v
    node --check docs/biological-data-center/app.js
    python3 scripts/xunia_bio_cl1.py --check
    bash -n scripts/xunia-bio

GitHub Pages deployment is a separate step. This branch alone does not activate the domain: merge a reviewed PR and verify the Pages workflow first.

## Security/truth boundaries

- No Vercel or paid/cloud inference service.
- No public exposure of the operator's host telemetry.
- No connected physical neurons, biological sensors, medical signals or clinical claims.
- No bank integrations, financial actions, Glass Onion private-vault unlocking or privileged system controls.
- No invented service health: public Pages reports STATIC / NOT LIVE.
- No claim of production deployment until GitHub Pages actually publishes the branch.
