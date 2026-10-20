# XUNIA Cyber Defense Learning Swarm

**Publication route:** https://xunia.org/cyber-swarm/
**Canonical repo:** sonoxo/gpt-doug-llm (`docs/cyber-swarm/`)
**Release:** 2026-10-20 / `xunia.cyber.swarm.curriculum.v1`

Free, browser-first **defensive** cyber learning. The website is hosted as static files on GitHub Pages. It is connected through the XUNIA Museum navigation, resources catalog, Universal Hive architecture, and Tasmania digital-twin demo.

## Exactly what executes

- **15 fictional labs**, covering the 15 Enterprise ATT&CK tactic categories (not all individual techniques or sub-techniques).
- **6 deterministic browser roles**: Scope Guard, ATT&CK Mapper, Signal Analyst, Defense Builder, Chaos Critic, Evidence Verifier.
- Original synthetic events, safe analyst checkpoints, score tracking stored locally in browser storage, and JSON report download.
- Links to **official MITRE ATT&CK, MITRE D3FEND, NIST CSF 2.0, OWASP WSTG, and CISA KEV** sources.
- No model API, remote workers, real scans, credential access, malware execution, autonomous intrusion, or targeting.
- No dependency on paid tools or network fetches except the local `curriculum.json` and optional outbound links when clicked.

## Local operation

From the repository root:

```sh
python3 -m http.server 8000 --directory docs
# Visit http://127.0.0.1:8000/cyber-swarm/
```

## Verification

```sh
node --check docs/cyber-swarm/engine.mjs
node --check docs/cyber-swarm/app.mjs
node --test tests/cyber_swarm.test.mjs
```

Browser smoke checks with Playwright and installed Chromium run against local in-memory HTML/assets due to this environment's loopback browser navigation policy; this validates key UI interactions but not final public-site rendering. GitHub Pages must separately confirm the public route, scripts and valid curriculum. The public Pages workflow is the deployment source of truth.

## Provenance and boundaries

- Enterprise ATT&CK tactic IDs and reference links: https://attack.mitre.org/tactics/
- Countermeasure taxonomy: https://d3fend.mitre.org/
- CSF 2.0 functions: https://www.nist.gov/cyberframework
- Web testing guidance: https://owasp.org/www-project-web-security-testing-guide/
- KEV prioritization context: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

XUNIA's role outputs are **original synthetic training examples**. They do not constitute MITRE/NIST/CISA certification, real-world incident verdicts, continuous learning, or a standing agent network. Interact with external systems only when expressly authorized.
