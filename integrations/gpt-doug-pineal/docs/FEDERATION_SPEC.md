# ZYRA Federation and Terminal Cortex Specification

## Purpose
Turn GPT-DOUG-PINEAL into a locally runnable, ontology-first observation hub and graphical terminal for user-authorized biotechnology research, public commerce/markets, social platforms, computing infrastructure, and defensive security system health.

## Boundaries
- Node names such as Meta, Tesla, X, Snapchat, LinkedIn, and global markets represent connector templates, NOT active access, affiliation, or endorsement.
- Never make network calls or assert external real-time data in the default installation. Until an approved connector is implemented, records are either local manual observations or visibly synthetic examples.
- Defense node is for non-sensitive, synthetic, aggregate defensive readiness/SI training only. No targeting, kinetic guidance, classified/CUI data, reconnaissance, or weapon-system commands.
- Biotechnology node is for public/synthetic aggregates and research metadata. No personal brain or medical records, unsupported decoding of thoughts, neural stimulation, or hidden model reasoning.
- All observations must be provenance-tagged and policy-validated, stored locally in SQLite with a hash-chain audit entry. No third-party credentials are accepted as observation values.
- Show status of all connector templates explicitly as OFFLINE / NOT CONNECTED, even when imported observations exist.
- Use Python >=3.10, standard library runtime, pytest tests, and ANSI or plain-text Mac terminal visualization. No paid accounts required.

## Interfaces
- `pineal federation`: show registry and actual connection status.
- `pineal observe NODE METRIC VALUE --unit UNIT --source SOURCE [--synthetic]`: record numeric observation with source and policy checks.
- `pineal dashboard --demo [--watch] [--interval N] [--frames N] [--no-color]`: visualize provider registry, local observation trends, synthetic demo signals, existing Kraken telemetry, audit state and defensive shields.
- `pineal dashboard` shows local-only observations; no synthetic metrics unless --demo.
- Local read-only API route `GET /v1/federation` provides connected=false registry and recent observation summary, authenticated like existing endpoints. No external ingestion via HTTP in this phase.

## Acceptance
- Baseline suite remains green.
- Policy rejects unknown nodes, secret-like strings, invalid values, unsupported classifications and sensitive defense/biotech topics.
- Observations are audited; mistaken or unproven connections are never reported as live.
- Dashboard runs in non-TTY pipelines, displays a static local view and a clearly labeled simulation view, supports bounded --frames for tests, and uses terminal-safe rendering.
- Mac install command uses verified git subdirectory from sonoxo/gpt-doug-llm feature branch.
