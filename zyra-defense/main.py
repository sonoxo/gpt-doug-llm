from fastapi import FastAPI

app = FastAPI(
    title="ZYRA Defense Ontology",
    version="0.1.0",
    description="Simulation-only ZYRA defense ontology service.",
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "zyra-defense-ontology",
        "status": "ok",
        "mode": "simulation-only",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
