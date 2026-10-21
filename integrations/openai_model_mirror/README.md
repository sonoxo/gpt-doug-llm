# GPT-Doug OpenAI Open-Weight Mirror (REA)

**Scope:** Mirror publicly downloadable model repositories belonging to the verified OpenAI Hugging Face organization that have explicitly approved permissive licenses and ungated access. The catalog is discovered live, rather than hard-coded to four gpt-oss releases. Proprietary GPT-5/GPT-6/API-only model parameters cannot be recovered by REA.

## Requirements

- Python 3.9+; free huggingface_hub (`python3 -m pip install huggingface_hub`)
- Optional REA CLI (https://github.com/morluto/rea); Node.js 22.19+ / 24.11+ / 26+ per upstream
- Sufficient storage for model snapshots: some models are tens of GB; full mirroring can require substantial disk space and GPU capacity to run

From the **gpt-doug-llm repository root**:

```sh
python3 -m integrations.openai_model_mirror catalog
python3 -m integrations.openai_model_mirror plan --all
python3 -m integrations.openai_model_mirror plan --models openai/gpt-oss-20b
python3 -m integrations.openai_model_mirror sync --models openai/gpt-oss-20b --max-gb 30 --yes
python3 -m integrations.openai_model_mirror inspect --model openai/gpt-oss-20b
# After reviewing the plan and provisioning storage:
python3 -m integrations.openai_model_mirror sync --all --max-gb 1000 --yes --allow-partial
python3 -m unittest discover -s tests -p 'test_openai_model_mirror.py' -v
```

The storage budget in the all-model command is an **example only** and not a capacity estimate. The code refuses an insufficient budget or disk space. By default, any unapproved repository blocks a whole batch. `--allow-partial` explicitly permits skipping unknown-license, gated, disabled, empty or unverifiable repositories and reports these skips.

The default destination is `~/.cache/gpt-doug/openai-models`, outside GitHub. Every download is pinned to the official Hub revision and accompanied by local SHA-256 file manifest. Downloaded code is **not executed**. REA statically analyzes existing safetensors and GGUF metadata and stores evidence in `.rea-evidence`; it does **not** clone weights, run model inference, or recover proprietary parameters. Other formats are mirrored but not analyzed by REA.

The gpt-oss models use Apache 2.0 with a usage policy. Review https://openai.com/open-models/ and https://github.com/openai/gpt-oss . Other OpenAI models retain their own applicable licenses and restrictions.

No credential bypass, token scraping, private access, autonomous replication or remote deployment. Network use occurs only after catalog/plan/sync commands and only through the official Hugging Face client with anonymous `token=False`. Review model licenses, source trust, disk requirements and security policies before downloading.
