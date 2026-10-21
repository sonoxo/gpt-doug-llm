# XUNIA Museum: GPT-Doug 99,999,999 Virtual-Agent REA Fleet

**Stage:** locally tested, bounded logical-fleet simulator. No hosted inference, remote clones, spacecraft connection, or autonomous deployment.

- **99,999,999 deterministic logical agent IDs** occupy 8 partitions by default.
- **One model identity**, default public OpenAI `gpt-oss-20b`, supports the index; model bytes are not duplicated.
- **REA evidence opt-in:** static metadata analysis of an operator-installed public .gguf/.safetensors model, with SHA-256 digest recorded in the fleet plan.
- **Governance:** no satellite uplinks, autonomous self-replication, network discovery, remote calls, or worker processes.
- **Proof:** offline Python unit tests for exact partitioning, bounded allocations, REA link, and exclusive JSON manifest.

Launch: `bash scripts/doug-rea-swarm --count 99999999 --slots 8`.

[Operator guide](../../integrations/openai_model_mirror/SWARM.md) | [Source](../../integrations/openai_model_mirror/swarm.py)
