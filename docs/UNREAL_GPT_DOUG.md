# UNREAL-GPT-DOUG // Unreal Engine 5.8 Learning Profile

Status: **ACTIVE_SOURCE_GROUNDED_PROFILE**

This package turns the August 2026 Epic learning roundup into a persistent, provenance-aware GPT-Doug knowledge layer. It does **not** claim that model weights were retrained. Instead, GPT-Doug retrieves curated UE 5.8 knowledge entries and injects them into Unreal-related prompts before model inference.

## Source hierarchy

1. Epic Games first-party UE 5.8 documentation and release notes.
2. Epic-authored articles and sample-project notes.
3. Community tutorials explicitly linked by Epic.
4. GPT-Doug synthesis only when labeled as project policy or derived guidance.

Community guidance never overrides first-party API behavior or feature maturity.

## Learned framework map

```text
UNREAL ENGINE 5.8
├─ FOUNDATION
│  ├─ C++ / UObject / reflection
│  ├─ Blueprints
│  ├─ Gameplay Framework
│  ├─ Modules / Plugins
│  └─ UnrealBuildTool
├─ GAMEPLAY
│  ├─ Gameplay Ability System
│  ├─ Enhanced Input
│  ├─ StateTree
│  ├─ Smart Objects
│  └─ Mover
├─ NETWORKING
│  ├─ authoritative server/client replication
│  ├─ Iris
│  ├─ Replication Graph
│  ├─ Dedicated Servers
│  └─ Networked Physics
├─ ANIMATION + SIMULATION
│  ├─ Motion Matching / Pose Search
│  ├─ Control Rig
│  ├─ Physics Control / ragdoll
│  └─ Chaos Physics
├─ AUDIO + VFX
│  ├─ Audio Engine
│  ├─ MetaSounds
│  └─ Niagara
├─ WORLDS + RENDERING
│  ├─ World Partition / HLOD
│  ├─ PCG / Mesh Terrain
│  ├─ Nanite
│  ├─ Lumen
│  └─ Materials
├─ CINEMATICS + VP
│  ├─ Sequencer
│  ├─ Movie Render Graph / Queue
│  ├─ Accumulation DOF
│  └─ nDisplay / Live Link / ICVFX
├─ BUILD + INFRA
│  ├─ UAT / BuildCookRun
│  ├─ BuildGraph
│  ├─ Horde
│  ├─ Gauntlet
│  ├─ Automation Test Framework
│  └─ Unreal Insights
└─ AI EDITOR CONTROL
   └─ Unreal MCP / ModelContextProtocol / AllToolsets
```

## GPT-Doug integration

The top-level GPT-Doug terminal exposes:

```text
/unreal
/unreal on
/unreal off
/unreal search <query>
/unreal sources [query]
/unreal mcp
```

When Unreal mode is active, only prompts matching Unreal vocabulary receive UE context, so unrelated GPT-Doug conversations are not polluted with engine material.

The existing `workers/knowledge/*.jsonl` ontology loader automatically ingests `workers/knowledge/unreal-engine-5-8.jsonl`, so the knowledge is also available through the existing `/knowledge` path and worker retrieval pipeline.

## Unreal MCP boundary

Epic's UE 5.8 Unreal MCP plugin is experimental. The official architecture embeds a local MCP server inside the Editor and exposes editor functions as tools. GPT-Doug treats this as a bounded editor adapter:

```text
USER INTENT
  -> GPT-DOUG PLAN
  -> SOURCE-GROUNDED UE KNOWLEDGE
  -> UNREAL MCP TOOL DISCOVERY
  -> USER PROJECT / SOURCE CONTROL
  -> EDITOR MUTATION
  -> AUTOMATION TEST
  -> INSIGHTS / LOG / SCREENSHOT VERIFICATION
  -> RESULT + PROVENANCE
```

The Unreal Editor and project files remain the execution source of truth. Keep the MCP server local unless a secure remote design is intentionally implemented.

## Feature maturity

UE 5.8 documentation marks several learned systems experimental, including Iris, Mover, Mesh Terrain, Accumulation Depth of Field, and Unreal MCP. GPT-Doug must preserve those labels and must not silently present them as production-stable.

## Primary seed

Epic Games, *August’s Epic learning content: Networked physics, dynamic audio, and more*, August 28, 2026.

See `sources.json` for the complete provenance registry and `ontology.json` for the machine-readable framework map.
