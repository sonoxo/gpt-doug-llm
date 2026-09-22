from __future__ import annotations

from .types import Integration, Stage


INTEGRATIONS: tuple[Integration, ...] = (
    Integration(
        "hermes-agent",
        Stage.EXECUTE,
        "NousResearch/hermes-agent",
        "Primary agent shell, delegation, scheduling, terminal backends, and skill loop.",
        "command",
        "hermes",
        required=True,
    ),
    Integration(
        "openspec",
        Stage.DEFINE,
        "Fission-AI/OpenSpec",
        "Behavior-first change specs and cross-repository planning artifacts.",
        "command",
        "openspec",
    ),
    Integration(
        "spec-kit",
        Stage.DEFINE,
        "github/spec-kit",
        "Spec-driven development workflows and implementation convergence.",
        "command",
        "specify",
    ),
    Integration(
        "caveman",
        Stage.COMPRESS,
        "JuliusBrussee/caveman",
        "Compact agent input/output while preserving exact recoverability.",
        "command",
        "caveman",
    ),
    Integration(
        "scrapling",
        Stage.COLLECT,
        "D4Vinci/Scrapling",
        "Adaptive web collection and crawl layer.",
        "python_module",
        "scrapling",
    ),
    Integration(
        "docling",
        Stage.PARSE,
        "docling-project/docling",
        "Structured parsing for PDFs, office files, HTML, media, and images.",
        "python_module",
        "docling",
    ),
    Integration(
        "pageindex",
        Stage.RETRIEVE,
        "VectifyAI/PageIndex",
        "Reasoning-based document retrieval over hierarchical indexes.",
        "python_module",
        "pageindex",
    ),
    Integration(
        "mem0",
        Stage.REMEMBER,
        "mem0ai/mem0",
        "Persistent cross-session and multi-agent memory.",
        "python_module",
        "mem0",
    ),
    Integration(
        "headroom",
        Stage.COMPRESS,
        "headroomlabs-ai/headroom",
        "Context compression for tool outputs, logs, files, and RAG payloads.",
        "python_module",
        "headroom",
    ),
    Integration(
        "daytona",
        Stage.EXECUTE,
        "daytonaio/daytona",
        "Optional legacy sandbox adapter; public repository is unmaintained as of June 2026.",
        "command",
        "daytona",
        notes="legacy_optional",
    ),
    Integration(
        "trendradar",
        Stage.WATCH,
        "sansan0/TrendRadar",
        "Trend/RSS monitoring and MCP-backed change detection.",
        "env",
        "TREND_RADAR_MCP_URL",
    ),
    Integration(
        "fabric",
        Stage.DEFINE,
        "danielmiessler/Fabric",
        "Reusable task patterns for analysis, extraction, transformation, and review.",
        "command",
        "fabric",
    ),
    Integration(
        "hyperframes",
        Stage.SHIP,
        "heygen-com/hyperframes",
        "Deterministic HTML-to-video rendering for agent-authored output.",
        "command",
        "hyperframes",
    ),
    Integration(
        "openmontage",
        Stage.SHIP,
        "calesthio/OpenMontage",
        "Agentic research-to-video production and montage pipeline.",
        "env",
        "OPENMONTAGE_HOME",
    ),
    Integration(
        "ai-engineering-hub",
        Stage.DEFINE,
        "patchy631/ai-engineering-hub",
        "Reference corpus of implementation patterns and production examples.",
        "reference",
        "https://github.com/patchy631/ai-engineering-hub",
    ),
)

BY_SLUG = {item.slug: item for item in INTEGRATIONS}
BY_STAGE = {
    stage: tuple(item for item in INTEGRATIONS if item.stage is stage)
    for stage in Stage
}
