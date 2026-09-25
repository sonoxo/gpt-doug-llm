# NUCLR Global Telemetry Pipeline

Telemetry/simulation-only nuclear-energy pipeline for XUNIA / ZYRA / GPT-Doug.

## Scope

Accepts aggregated **public** or **synthetic** energy-health signals and emits a read-only `NUCLR` component for the Global Charge model. It never connects to plant control networks and contains no startup, shutdown, setpoint, valve, pump, control-rod, targeting, credential, or command-dispatch capability.

## Input

Each regional record contains only:

- `availability_pct`
- `reporting_coverage_pct`
- `generation_pct_of_reference`
- `data_freshness_minutes`
- `provenance`: `public` or `synthetic`

## Output

The pipeline emits a `0-100` advisory charge component, state (`LOW`, `NOMINAL`, `HIGH`, `SURGE`), provenance confidence, regional scores, and explicit `external_actuation: false`.

## Run the synthetic test fixture

```bash
python nuclear/global_pipeline/pipeline.py \
  nuclear/global_pipeline/sample.synthetic.json
```

## Safety contract

The parser recursively rejects operational/control fields. The output is advisory telemetry only; it is not an authorization or control signal for any nuclear, grid, defense, or other protected infrastructure.
