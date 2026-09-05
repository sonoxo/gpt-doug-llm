# GPT-DOUG POCKET Publication Benchmark Protocol

This protocol is designed to produce evidence suitable for a technical write-up, README benchmark table, preprint, demo paper, or reproducibility appendix.

## Claim boundary

The benchmark does **not** claim GPT-DOUG POCKET is the first portable local LLM on macOS. The intended contribution claim is narrower and testable:

> GPT-DOUG POCKET is a USB-resident local AI agent environment for macOS that places the repository, model cache, persistent memory, workspace, logs, and runtime state on removable storage while using the host Mac for local inference compute through llama.cpp, with a loopback OpenAI-compatible API and GitHub-based recovery/synchronization.

## Metrics

The benchmark records:

1. **Restart-to-health latency** — time from stopping the Pocket-owned llama process to a healthy `/v1/models` response.
2. **End-to-end generation throughput** — completion tokens divided by wall-clock generation time for a fixed prompt.
3. **USB allocation delta** — filesystem used-block change on the Pocket volume during the benchmark.
4. **Internal filesystem allocation delta** — used-block change on the host home filesystem during the same interval. This is an observable allocation proxy, not raw physical I/O.
5. **Metal runtime evidence** — matching llama.cpp Metal/GPU initialization lines in the Pocket runtime log.
6. **Persistence across Macs** — a USB-resident persistence record tracks privacy-preserving host signatures and run count. Running the same drive on a second Mac changes `distinct_host_count` from 1 to 2+.
7. **Recovery behavior** — the benchmark intentionally performs a stop/start cycle and requires API health afterward.
8. **Zero-paid-API execution evidence** — the inference endpoint is loopback-only and the harness records the llama process's socket state after generation. The benchmark itself performs no paid API calls.

## Run

On the Mac with GPT-DOUG POCKET mounted:

```bash
"/Volumes/NO NAME/GPT-DOUG/gpt-doug" sync
"/Volumes/NO NAME/GPT-DOUG/gpt-doug" benchmark
```

If the drive is renamed, replace `/Volumes/NO NAME` with its mounted path.

Results are written to:

```text
GPT-DOUG/benchmarks/results/
├── benchmark-YYYYMMDD-HHMMSS.json
└── benchmark-YYYYMMDD-HHMMSS.md
```

The cross-machine persistence record is written to:

```text
GPT-DOUG/benchmarks/persistence.json
```

## Cross-Mac portability test

1. Run the benchmark on Mac A.
2. Stop Pocket cleanly:

```bash
"/Volumes/NO NAME/GPT-DOUG/gpt-doug" stop
```

3. Eject the drive normally.
4. Connect the same drive to Mac B.
5. Start and run the benchmark again.
6. Confirm the result reports:

```text
Distinct Macs observed by same Pocket state: 2
Cross-Mac persistence observed: True
```

Do not publish raw hostnames or serial numbers. The benchmark stores only a truncated SHA-256 host signature plus non-sensitive hardware class information.

## Metal utilization

The default benchmark records **Metal backend evidence**, which is reproducible without privilege escalation. A formal paper that reports actual GPU utilization should additionally collect a short privileged `powermetrics` sample while inference runs.

Example manual collection on macOS:

```bash
sudo powermetrics --samplers gpu_power -i 1000 -n 10 > "/Volumes/NO NAME/GPT-DOUG/benchmarks/powermetrics.txt"
```

Run the fixed inference benchmark during that sampling interval. Availability and sampler names can vary by macOS/hardware version, so the raw file should be retained with the publication artifacts.

## Internal SSD write methodology

`df` allocation delta is deliberately labeled as an allocation proxy. It should not be represented as exact NAND bytes written.

For stronger write-path evidence, a publication run may additionally use macOS `fs_usage` during inference and retain the raw trace. The analysis should distinguish:

- writes under `/Volumes/<Pocket>/GPT-DOUG/...`
- writes under the user's internal home directory
- OS-level unrelated writes from other processes

The core architectural claim is that GPT-DOUG's configured model cache, application cache, logs, memory, workspace, temp directory, and runtime state resolve to the Pocket volume.

## Reproducibility controls

For comparable results:

- use the same model and quantization;
- use the same fixed prompt;
- use `temperature=0`;
- use the same `max_tokens` value;
- record macOS version, hardware model, chip, memory, repository commit, and model ID;
- run at least 5 trials per hardware configuration;
- report median, minimum, maximum, and standard deviation;
- state whether the model was already cached before the trial;
- state USB interface/media type when known (USB 2, USB 3, SSD enclosure, etc.).

## Suggested paper table

| Host | Storage | Model | Restart→health | tok/s | Internal allocation Δ | Metal | Recovery | Paid API |
|---|---|---|---:|---:|---:|---|---|---|
| Mac A | USB | Qwen3 0.6B Q4 | TBD | TBD | TBD | Yes/No | Pass/Fail | No |
| Mac B | same USB | same model | TBD | TBD | TBD | Yes/No | Pass/Fail | No |

## Publication language

Use claims like:

- “USB-resident local AI agent environment”
- “host-compute / removable-state architecture”
- “portable persistent local inference environment”
- “loopback OpenAI-compatible local runtime”
- “cross-Mac persistent workspace and model cache”

Avoid unsupported claims such as “first ever,” “zero internal writes” unless raw tracing proves it, or “no network access” if model synchronization/download traffic occurred during the run.
