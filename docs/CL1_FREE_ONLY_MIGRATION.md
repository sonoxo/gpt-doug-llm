# CL1 / GPT-DOUG: free-only infrastructure migration

## Non-negotiable operating policy

**No paid API calls, commercial compute provisioning, metered deployment, or unattended billing.** The CL1 inference boundary blocks OpenAI, Anthropic, Gemini, Ollama `:cloud` model names and other remote inference in the GPT-DOUG provider facade **even if** a developer accidentally supplies keys or sets `PAID_MODE=true`. Requests are served only by a locally operated Ollama model (or offline planning mode when no model is available). Cloud services elsewhere in the fleet have NOT been disabled by this single safeguard and must be inventoried individually.

"Free" here means no mandatory license or API subscription. Hardware, power, disk, bandwidth, public domains and commercial-provider free tiers can still cost money. Do not silently upgrade a free tier or enable paid overages.

## Target architecture

| CL1 capability | Free-only target | Constraints |
| --- | --- | --- |
| AI inference | Ollama + a compatible locally downloaded open-weight model | Requires owner-supplied hardware; verify model license |
| Model coordination | GPT-DOUG local provider facade + bounded local swarm | No remote model fallback |
| API and app | Python local HTTP backend / Node app on localhost | No cloud deployment or open public port by default |
| Database | SQLite for single-machine experiments; self-host PostgreSQL if necessary | Back up data before changes |
| Static frontend / docs | GitHub Pages for public static content | Not suitable for secrets or backend workloads |
| Source, CI, dependency review | Public GitHub repo, GitHub Actions standard public runners, Dependabot PRs | Respect usage/storage limits; no paid runners or blanket merges |
| Container builds | Local Docker-compatible engine or Podman | No paid registry/compute assumption |
| Discovery / search | Locally hosted SearXNG when lawful and rate-limited | Search engines can limit or block access |
| Monitoring | Existing local health scripts, JSON audit logs and offline reports | No external monitoring subscriptions |
| NXYZ personal cloud | Existing Mac / owned computer / external HDD | Backup, encryption and availability are operator responsibilities |

## Observed legacy dependencies; migration status

1. **GPT-DOUG**: The previous provider router listed paid cloud inference ahead of Ollama in its automatic fallback order. CL1 blocks remote inference in the main provider facade and sets local-only defaults. Existing independent modules must be audited separately.
2. **Vercel**: Git-based deployment is already disabled in the root `vercel.json`; blocked external Vercel checks are *not* proof of a free or functioning deployment. Do not create a new Vercel deployment.
3. **Render**: `render.platform.yaml` is an optional legacy free-plan blueprint; its availability and limits are provider-dependent. Do not provision it as part of CL1; prefer localhost and public static GitHub Pages.
4. **Zyra**: The example environment references Stripe, Resend, Replit and hosted PostgreSQL. Before any actual cutover, identify live usages, replace outbound email with a local mail draft/export where adequate, remove payments from the free-only execution path, and migrate any data with a verified backup. Do not delete user data or disable a live production route without validation.
5. **XUNIA Hub**: The example environment references AI Gateway, Vercel Blob, AWS and Redis. Keep any AI Gateway key unset; use local Ollama and self-hosted storage where code supports it. These are follow-up repo-specific changes, not presumed complete.
6. **Palantir Foundry/AIP and third-party APIs**: optional tenant-specific access is **not** a free fallback. Disable chargeable integrations unless entitlements and exact zero-cost boundaries are independently verified.

## Local Mac deployment (no subscriptions)

Install the open-source Ollama runtime by the operator's preferred package manager or official installer. From the GPT-DOUG checkout run:

```bash
ollama serve
# In another terminal, after choosing an appropriate licensed model:
ollama pull qwen2.5-coder:3b
bash scripts/cl1-free-swarm.sh doctor
bash scripts/cl1-free-swarm.sh run
```

The launcher refuses non-loopback Ollama URLs and refuses to start when local inference is unavailable. It never supplies paid credentials or installs/downloads dependencies on its own.

## Migration gates (fail-closed)

- [x] Create zero-billing inference policy and offline regression tests.
- [x] Default GPT-DOUG local launch to Ollama and reject remote inference in its provider transport.
- [ ] Merge the CL1 PR after CI passes; verify live local Ollama and model availability on operator machine.
- [ ] Audit each Sonoxo repository for paid API keys, hosted billing, email, storage and data transfer.
- [ ] Back up every live database/object store; test restores before cutover.
- [ ] Move each backend and scheduled job onto owned infrastructure using individual per-repo PRs.
- [ ] Validate authentication, static site availability, mobile access, backups, observability and rollback.
- [ ] Disconnect/cancel old paid subscriptions manually in their billing consoles after verified service migration.

**Scope boundary:** GitHub commits alone cannot migrate existing billing accounts, DNS, managed databases, cloud resources or private production data. Never claim an active paid subscription was canceled because a repository configuration changed.
