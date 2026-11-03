# GPT-DOUG Open-Weight Model Factory

Generate reproducible training *plans* for arbitrarily many LoRA model variants (in bounded batches). Train individual variants locally with Hugging Face Transformers + PEFT. Plans do **not** contain trained model weights.

## 1. Generate three manifests (standard library only)

```bash
python3 research/model_factory/factory.py plan --base-model Qwen/Qwen2.5-0.5B --dataset data/train.jsonl --count 3 --rank 8 --output model_plans
```

Each JSON manifest has a stable identifier, independent random seed, LoRA rank, step limit and base-model reference. The planned batch is limited to 1–1000 records per command. Repeat with distinct names and seeds for further configurations.

## 2. Prepare data

Create a UTF-8 JSONL file with one `{"text":"..."}` object per line. Obtain permission to use the training data. Do not include secrets or personal information.

## 3. Train an adapter (optional)

```bash
python3 -m pip install torch transformers peft datasets accelerate
python3 research/model_factory/factory.py train --manifest model_plans/<your-manifest>.json --output model_outputs/model1
```

Replace `<your-manifest>` with a generated filename. Download access, model licenses, hardware capacity and dependencies are the user's responsibility. On Apple Silicon, PyTorch may support MPS; on Intel Macs, CPU fine-tuning can be slow. Start with a small model and short training run.

Outputs under `model_outputs/model1/adapter` are LoRA adapter weights and tokenizer files, **not independent full model weights**. Load them with a compatible base model.

### Resource and validation limitations

- There is no infinite compute, infinite memory or zero-cost unlimited training.
- The factory does not circumvent model access restrictions, licenses, service quotas or hardware limits.
- Use a truly open-weight base under appropriate license, and review terms individually.
- No trained adapters or performance benchmarks are included in this repository change.
- Test correctness and measure quality before deploying any trained model.
