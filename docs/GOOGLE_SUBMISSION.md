# All Things Agentic Hackathon — Submission Text

## Project Name
GPT Doug LLM — Fortified Enterprise Fleet: Zero-Trust Agent Network with Built-in Cybersecurity

## Track
The Fortified Enterprise Fleet — enterprise-grade, zero-trust network of agents that can be discovered, governed, and scaled safely inside a large organization.

## One-Liner
A zero-trust network of autonomous security agents built on Zyra 3.0 (watchdog), Golden Shield (perimeter defense), and Sentinel (24/7 scanner) — deployed on Google Cloud Run, orchestrated by Google ADK, powered by Gemini 3.5, with 173 knowledge entries and 103 passing tests.

## Full Description

### Problem
Enterprise AI agent deployments lack security by default. Agents handle sensitive data with no guardrails, no audit trail, no threat detection. Existing agent frameworks (LangChain, CrewAI, AutoGen) have no built-in security layer. Enterprises need agents that are autonomous AND trustworthy.

### Solution
GPT Doug LLM is a zero-trust agent network where every request passes through 5 security layers before reaching an agent:

1. **Golden Shield** — Perimeter defense. Eliminates threats (botnet, reverse shell, cryptominer, rootkit), rate-limits floods, bans malicious sources. 14 threat elimination patterns.

2. **Zyra 3.0** — Input/output inspection. Redacts secrets (API keys, private keys, credentials), blocks destructive commands, detects prompt injection, classifies sensitivity (UNCLASSIFIED→TOP_SECRET), tags social engineering (RICE framework), writes HMAC-chained tamper-evident audit logs.

3. **Compliance Gate** — Jurisdiction-aware policy. Blocks autonomous weapons, social scoring, protected-trait inference. Maps to NIST AI RMF.

4. **Three-Factor Auth** — Verified business email + E.164 phone + TOTP. Consumer email domains rejected.

5. **ASTRAL** — Two-person governance. Independent security officer required for elevation. 5-minute sessions, 20-command cap, 5-failure lockout.

### Google Cloud Integration (Mandatory Requirements)
- **Gemini 3.5 API** — Used as the LLM backend via `google/gemini_backend.py`. Drop-in replacement for Ollama/OpenAI. Same interface, so agent_chain works with any backend.
- **Google ADK** — Agent orchestration via `google/adk_wrapper.py`. 6 tools registered: zyra_inspect, sentinel_scan, golden_shield_check, knowledge_search, code_review, crypto_anchor.
- **Google Cloud Run** — Hosts the API Gateway. Public URL for judges: `https://gpt-doug-api-us-central1-PROJECT.run.app`
- **Firestore** — Agent registry (discoverable agents), scan results (trend analysis), knowledge base (173 entries synced from JSONL), audit logs (mirrored from HMAC chain).
- **Pub/Sub** — Agent task coordination. Publish task → subscription picks it up → agent runs → result to Firestore.

### The 10 Agents
Deployed as a fleet, discoverable via Firestore, coordinated via Pub/Sub:

**Everyday:** Sentinel Bot (home security), Meeting Sentinel (calendar), Health Tracker (medications), Expense Sentinel (receipts)
**Professional:** Document Drafter (contracts), Invoice Ninja (freelance payments), Code Reviewer ★ (PR review)
**Good Neighbor:** NeighborHelp (food bank), Emergency Mesh (neighborhood), School Coordinator (PTA)

### Architecture
```
User → Cloud Run → Golden Shield → Zyra 3.0 → ADK → Agent → Output Sterilize → User
                    ↓                              ↓              ↓
               Sentinel (24/7)              Gemini 3.5      Firestore
                                                  ↓
                                             Pub/Sub
```

### Technologies Used
Python, Gemini 3.5 API, Google ADK, Google Cloud Run, Firestore, Pub/Sub, Ollama (local fallback), Stripe, Twilio, CoinGecko API, MIT License

### Data Sources
- NIST NVD CVE feed (external vulnerability scanning)
- CISA Known Exploited Vulnerabilities
- GitHub Security Advisories
- CelesTrak/NORAD satellite tracking
- 173-entry knowledge base (IBM, CIA, FBI, MIT, TechForce — all public sources)

### Findings & Learnings
- Security is a feature, not an add-on. Agents with built-in security are more valuable than agents without.
- 125-payload DDoS simulation: 100% attack block rate, 0% false positives.
- "Only surface when needed" principle: agents run autonomously and only alert humans for genuine judgment calls.
- Zero-budget deployment is possible: GitHub Actions + Cloud Run free tier + Firestore free tier + Pub/Sub free tier = $0.

### Spin-Up Instructions
See README.md → Quick Start section. Full deployment guide in `google/cloud_run.py`.

### Bonus Points
- Blog post: `docs/BUILD_STORY.md` (ready to publish on Medium/dev.to)
- Social: Post with #AllThingsAgenticHackathon
- Gemma: `models/Modelfile.qwen3` — local Gemma integration via Ollama

### Numbers
- 14,849+ lines of code
- 160+ files
- 103 tests passing
- 173 knowledge entries
- 39 commits
- MIT licensed
- $0 budget
