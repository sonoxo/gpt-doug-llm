#!/usr/bin/env python3
"""GPT-DOUG open-weight model factory. Plans are not trained models."""
import argparse
import hashlib
import json
import pathlib
import random
import re
import sys
from datetime import datetime, timezone

def safe_name(value):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}", value):
        raise ValueError("invalid name")
    return value

def plan(args):
    out = pathlib.Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not 1 <= args.count <= 1000:
        raise ValueError("count must be between 1 and 1000 per invocation")
    if not 1 <= args.rank <= 256:
        raise ValueError("rank must be between 1 and 256")
    if not 1 <= args.steps <= 100000:
        raise ValueError("steps must be between 1 and 100000")
    if not args.base_model or not args.base_model.strip():
        raise ValueError("base model is required")
    tag = safe_name(args.name)
    rng = random.Random(args.seed)
    created = []
    for i in range(args.count):
        seed = rng.randrange(0, 2**31)
        identifier = "%s-%06d-%s" % (tag, i+1, hashlib.sha256(
            ("%s:%s:%s:%s" % (args.base_model, tag, args.seed, i)).encode()
        ).hexdigest()[:10])
        path = out / (identifier + ".json")
        if path.exists() and not args.overwrite:
            raise FileExistsError(str(path))
        record = dict(schema_version=1, id=identifier, kind="lora_training_plan",
                      status="PLANNED_NOT_TRAINED", base_model=args.base_model,
                      dataset=args.dataset, rank=args.rank, alpha=args.rank*2,
                      learning_rate=args.learning_rate, max_steps=args.steps,
                      seed=seed, created_at=datetime.now(timezone.utc).isoformat(),
                      note="Requires permitted base-weight access, adequate compute and approved dataset.")
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        created.append(str(path))
    print(json.dumps(dict(plans_created=len(created), directory=str(out),
                          status="PLANNED_NOT_TRAINED", first=created[0]), indent=2))

def train(args):
    manifest = json.loads(pathlib.Path(args.manifest).read_text(encoding="utf-8"))
    if manifest.get("kind") != "lora_training_plan":
        raise ValueError("not a supported manifest")
    if not manifest.get("dataset"):
        raise ValueError("manifest needs a JSONL dataset path")
    source = pathlib.Path(manifest["dataset"])
    if not source.is_file():
        raise FileNotFoundError(str(source))
    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model
        from transformers import (AutoModelForCausalLM, AutoTokenizer,
                                  Trainer, TrainingArguments, DataCollatorForLanguageModeling)
    except ImportError as exc:
        raise SystemExit("Install optional training dependencies: pip install torch transformers peft datasets accelerate") from exc
    rows = []
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record.get("text"), str) or not record["text"].strip():
            raise ValueError("dataset line %s requires nonempty text" % number)
        rows.append({"text": record["text"]})
    if not rows:
        raise ValueError("dataset is empty")
    model_id = manifest["base_model"]
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_id)
    model.config.use_cache = False
    cfg = LoraConfig(r=int(manifest["rank"]), lora_alpha=int(manifest["alpha"]),
                     task_type="CAUSAL_LM", lora_dropout=0.05)
    model = get_peft_model(model, cfg)
    ds = Dataset.from_list(rows)
    def encode(batch):
        return tokenizer(batch["text"], truncation=True, max_length=args.max_length)
    tokens = ds.map(encode, batched=True, remove_columns=["text"])
    output = pathlib.Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(output / "checkpoints"),
        max_steps=int(manifest["max_steps"]),
        per_device_train_batch_size=1, gradient_accumulation_steps=4,
        learning_rate=float(manifest["learning_rate"]),
        seed=int(manifest["seed"]),
        save_steps=100, logging_steps=10, report_to="none",
        fp16=False, bf16=False)
    trainer = Trainer(model=model, args=training_args, train_dataset=tokens,
                      data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False))
    trainer.train()
    model.save_pretrained(str(output / "adapter"))
    tokenizer.save_pretrained(str(output / "adapter"))
    print(json.dumps({"status": "TRAINED_ADAPTER", "path": str(output / "adapter"),
                      "base_model": model_id}, indent=2))

def main():
    p = argparse.ArgumentParser(description="Open-weight adapter training factory")
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("plan", help="Generate bounded training manifests")
    a.add_argument("--base-model", required=True)
    a.add_argument("--dataset", default="")
    a.add_argument("--name", default="gpt-doug")
    a.add_argument("--count", type=int, default=3)
    a.add_argument("--rank", type=int, default=8)
    a.add_argument("--steps", type=int, default=100)
    a.add_argument("--seed", type=int, default=42)
    a.add_argument("--learning-rate", type=float, default=0.0002)
    a.add_argument("--output", default="model_plans")
    a.add_argument("--overwrite", action="store_true")
    b = sub.add_parser("train", help="Train one PEFT LoRA adapter using local resources")
    b.add_argument("--manifest", required=True)
    b.add_argument("--output", default="trained_model")
    b.add_argument("--max-length", type=int, default=512)
    args = p.parse_args()
    try:
        if args.command == "plan":
            plan(args)
        else:
            train(args)
    except (OSError, ValueError, KeyError) as exc:
        p.exit(1, "Error: %s\n" % exc)

if __name__ == "__main__":
    main()
