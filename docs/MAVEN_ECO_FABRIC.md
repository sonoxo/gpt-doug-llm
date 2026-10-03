# MAVEN ECO FABRIC

MAVEN ECO FABRIC is the local runtime projection of the canonical XUNIA / GPT-DOUG-LLM ecosystem registry.

It does not create a new authority plane. It reads the existing ecosystem registry, AI-layer contract, and HIVE integration registry and turns them into a local runtime snapshot for operator visibility.

## Commands

```bash
python3 scripts/maven-eco-fabric.py doctor
python3 scripts/maven-eco-fabric.py status
python3 scripts/maven-eco-fabric.py snapshot --out ~/.gpt-doug/maven/eco-runtime.json

gpt-doug-maven eco-doctor
gpt-doug-maven eco
```

## Runtime snapshot

The generated `eco-runtime.json` contains:

- canonical control root, hub, domain registry, and execution plane
- core ecosystem planes
- domain routing
- six-layer AI contract
- internal divisions and research satellites
- runtime HIVE integration availability
- architecture rules and authority boundaries

The dashboard is local-first and reads the generated snapshot from the loopback MAVEN server.

## Authority

ECO FABRIC is an observability and routing surface. It does not convert model output, repository membership, or a declared capability into external authorization or execution authority.
