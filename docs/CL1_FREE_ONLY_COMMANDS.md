# CL1 / GPT-DOUG free-only commands

Run from the repository root on the Mac. No paid API key is required or accepted.

```bash
ollama serve
# In a second terminal:
ollama pull qwen2.5-coder:3b
bash scripts/cl1-free-swarm.sh doctor
bash scripts/cl1-free-swarm.sh run
```

Open `http://127.0.0.1:8787` on the same Mac. This intentionally binds the web server to loopback, not to an internet-exposed interface.

The launcher verifies that Ollama and the selected model already exist. It does not install software, download models, use an external compute service, create a paid account or provision cloud infrastructure. The `run` command refuses to start if the doctor fails. No background service is created.

To stop, press Ctrl+C in the running terminal. The server's paid task API remains disabled in CL1 free-only mode even if old payment credentials exist in the shell.

**Not yet migrated:** Zyra, XUNIA Hub, and any independently deployed external services. Use `docs/CL1_FREE_ONLY_MIGRATION.md` for the phased migration plan.
