# GPT-Doug AWS Prometheus bridge (free-first)

This deploys **one private GPT-Doug API gateway** (Python stdlib) plus a **local open-source Prometheus** collector. By default, it creates **no AWS resources**, starts **no AWS remote write**, and needs **no API keys or AWS account**. Docker/image download, computer power, disk and any provider usage are still your responsibility.

## Local-first setup

From the repository root:

```sh
python3 -m observability.prometheus_aws.configure
cd observability/prometheus_aws
docker compose up -d
docker compose ps
```

Open `http://127.0.0.1:9098/targets` to confirm the `gpt-doug-api` scrape target shows **UP**. Try PromQL `gpt_doug_api_uptime_seconds`, `gpt_doug_api_requests_total` and `rate(gpt_doug_api_requests_total[5m])`. Stop with `docker compose down` (omit `-v` to retain the data volume). Run `docker compose logs prometheus` for diagnosis. Docker is not required to test the exporter or config generator.

The gateway is deliberately **not published to host ports** and `/metrics` needs a random bearer token generated into the gitignored `runtime/` directory. Only Prometheus UI is published, bound to `127.0.0.1`. Prometheus scrapes one fixed target every **60s**, avoiding high-cardinality costs. Never expose this local stack on the public internet.

## Optional AWS Managed Service for Prometheus (AMP)

**AMP may incur usage charges**: cloud ingestion, storage, and queries can cost money, depending on your AWS Free Tier eligibility and quota. Nothing here claims AWS compute, services, or tokens are unlimited or free. AMP needs an *existing* workspace; this repository does **not create AWS resources** or send metrics until an operator deliberately enables remote write and starts Prometheus.

An operator who understands AWS charges can render an opt-in configuration using:

```sh
python3 -m observability.prometheus_aws.configure \
  --amp-region us-east-1 \
  --amp-workspace-id ws-REPLACE_WITH_YOUR_WORKSPACE_ID \
  --acknowledge-aws-charges
```

The generated `runtime/prometheus.yml` has a signed HTTPS `remote_write` destination with `sigv4.region`; only metrics matching `gpt_doug_.*` are forwarded. Restart Prometheus after changing mode:

```sh
cd observability/prometheus_aws
docker compose restart prometheus
```

**Authentication:** Provide the Prometheus container a trusted AWS SDK default credential source with **only** `aps:RemoteWrite` on the specific AMP workspace. Prefer an EC2 instance profile/ECS task role/EKS service account role on AWS; do **not** commit or embed access keys. Docker Compose on a local workstation does not automatically inherit host AWS credentials; configure an explicit trusted credential mechanism separately if you require local-to-AWS remote write. Endpoint format: `https://aps-workspaces.REGION.amazonaws.com/workspaces/WORKSPACE_ID/api/v1/remote_write`. No provider tokens, prompts or customer content are emitted as metrics.

**Disable AWS remote write immediately:** From repository root run `python3 -m observability.prometheus_aws.configure`, then `cd observability/prometheus_aws && docker compose restart prometheus`. Existing queued samples and AMP storage may still remain and may be billed. **Do not create an AMP workspace solely for this free-first demo.**

This monitors the contained gateway, not all separate running GPT-Doug/ZYRA/XUNIA processes. ZYRA Intelligence Cloud and XUNIA Platform already expose their own `/metrics` endpoints; add those authenticated, network-reachable scrape targets separately only under approved access controls. XUNIA metrics are viewer-authenticated by default. Their existing deployments are not modified here.

## Trust model

- No credentials in code, config output, Prometheus labels or Git; generated `runtime/` must remain ignored.
- No public ingress for GPT-Doug metrics; Prometheus UI loopback-only.
- Default config lacks `remote_write`; a billing acknowledgment is required to add AMP.
- Fixed route/status/method labels prevent unbounded time-series growth from user inputs.
- Generic gateway routes retain their existing behavior; the exporter is not an operational authorization boundary.
- Validated offline tests do **not** prove live AWS connectivity, working IAM or cloud deployment.

References: [AWS AMP ingest guide](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-onboard-ingest-metrics.html), [AMP pricing](https://aws.amazon.com/prometheus/pricing/), [Prometheus configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/).
