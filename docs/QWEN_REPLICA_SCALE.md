# Qwen Replica Scale-Out

GPT-Doug can distribute Qwen inference across multiple OpenAI-compatible replicas while preserving the existing single-endpoint configuration.

## Configuration

```bash
GPT_DOUG_PROVIDER=qwen
QWEN_MODEL=Qwen/Qwen3.8-Flash-Next
QWEN_BASE_URLS=http://127.0.0.1:8000/v1,http://127.0.0.1:8001/v1
GPT_DOUG_PROVIDER_MAX_INFLIGHT=4
GPT_DOUG_PROVIDER_RETRIES=1
GPT_DOUG_PROVIDER_COOLDOWN=10
```

`QWEN_BASE_URLS` takes precedence over `QWEN_BASE_URL`. If it is not set, the original `QWEN_BASE_URL` behavior remains unchanged.

## Scheduling

- Requests prefer the least-loaded healthy replica.
- Equal-load replicas rotate to spread work.
- Each replica has a bounded in-flight request count.
- Network failures, HTTP 408/425/429, and 5xx responses can fail over to another replica.
- Failed replicas enter a short process-local cooldown before they are preferred again.
- If every replica is at its configured in-flight limit, the gateway returns `provider_busy` instead of creating an unbounded queue.

## Security

The existing endpoint policy is retained: HTTPS is required for non-loopback endpoints; plain HTTP is accepted only for loopback addresses. Remote endpoints still require a configured Qwen/DashScope API key.

## Capacity model

With `R` replicas and `C=GPT_DOUG_PROVIDER_MAX_INFLIGHT`, the gateway exposes at most `R x C` concurrent request slots per GPT-Doug process. Actual throughput remains bounded by model size, context length, accelerator memory, batching behavior, and the serving engine (for example vLLM or SGLang).

Scale vertically first until a replica reaches an efficient accelerator utilization point, then add replicas horizontally. Benchmark tokens/second, time-to-first-token, p50/p95 latency, queue saturation, and error/failover rates before increasing concurrency.
