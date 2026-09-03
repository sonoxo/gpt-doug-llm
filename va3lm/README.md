# BIG VIRGINIA // VA3LM

**Virginia Agentic Large Learning Language Model — v0.6.0**

VA3LM is the Virginia/RVIA **agentic coding runtime and control plane** for the GPT-DOUG-LLM ecosystem. The brand name remains VA3LM, but the implementation does **not** claim that this repository trained a separate foundation model. A configured local OpenAI-compatible model supplies model reasoning; VA3LM supplies bounded memory, structured decisions, workspace tools, approval gates, evidence, ontology, geospatial/public-source modules, tests, and the 8088 command center.

## What is real now

- Port **8088** FastAPI command center.
- Local-model adapter through `VA3LM_MODEL_URL`.
- Structured coding-agent decision schema with validation and one structural repair attempt.
- Bounded tool loop with a maximum round budget instead of infinite autonomous loops.
- Workspace inspection and project detection.
- UTF-8 file reads/writes/deletes confined to a configured workspace.
- Automatic bounded backup before overwrite/delete and explicit restore support.
- Allow-listed development commands executed with `shell=False`.
- Command stdout/stderr/exit-code evidence.
- Human approval before workspace mutation or command execution.
- Model-token/secret filtering before child development processes.
- Recognized test/build/lint/security validation evidence instead of treating every exit-0 command as proof.
- PACK-inspired capability plane.
- Palantir-style local ontology blueprint.
- Authorized non-identifying geospatial tracking and Google Maps visualization.
- RVIA Federal Intel public-source catalog.
- Test, security, evidence, and CI gates.

## Exact execution boundary

VA3LM's **file tools** are workspace-confined: they reject absolute paths, path traversal outside the configured root, direct `.git` file access, and selected sensitive filenames. Development **subprocesses are different**: they start in the configured workspace, require explicit approval, use an executable allow-list, and run with `shell=False`, but they are **not an OS/container filesystem sandbox or a network sandbox**. Trusted project code can still access resources the local operating-system user can access.

That means local command execution is appropriate for trusted development work. A production multi-tenant coding cloud still needs a container/VM runner with explicit filesystem, process, resource, and network isolation.

Git commands are restricted to read-only subcommands in this runtime. Known package-manager `publish`, `deploy`, and `release` actions are blocked, but VA3LM does not claim that these checks constitute a complete network sandbox or universal deployment blocker.

## What VA3LM does **not** claim

- It is **not** a separately trained foundation model in this repository.
- The VA3LM ontology remains a local blueprint; it is **not** proof of a live Palantir Foundry Ontology deployment.
- It does **not** claim that an app was deployed or shipped unless a deployment provider actually returns evidence. v0.6.0 currently provides local coding/build/test execution, not a production cloud deployment plane.
- It does not grant itself Palantir, government, cloud, filesystem, shell, credential, or network permissions.
- Its local subprocess runner is **not** a container/VM security boundary.
- It is a private software project, not a U.S. government agency.

## Truthful coding loop

```text
GOAL
  ↓
PROJECT INSPECTION
  ↓
LOCAL MODEL DECISION
  ↓
JSON DECISION VALIDATOR
  ↓
READ / LIST / INSPECT
  ↓
APPROVAL GATE
  ↓
WRITE / DELETE / RUN COMMAND
  ↓
RUNTIME EVIDENCE
  ↓
MODEL REPAIR / NEXT ROUND
  ↓
VALIDATION
  ↓
COMPLETE WITH EVIDENCE OR STOP
```

Malformed model output no longer becomes a fake success state. VA3LM rejects unsupported actions and invalid decisions. It performs one structure-repair request; if the result is still invalid, execution stops with `INVALID_MODEL_DECISION`.

After a file mutation, the runtime requires a recognized successful validation command before it will accept the model's completion request. A random command that exits `0` is recorded as a successful command, but it is **not** reported as `testsProven` or `buildProven` unless it matches a recognized validation path.

## Run

```bash
cd va3lm
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
va3lm serve
```

Open `http://127.0.0.1:8088`.

## Configure the local brain

VA3LM only accepts the model endpoint on localhost.

```bash
export VA3LM_MODEL_URL=http://127.0.0.1:11434/v1
export VA3LM_MODEL_NAME=gpt-doug-llm-max
```

If no model URL is configured, `va3lm execute` returns `MODEL_NOT_CONFIGURED` plus a deterministic plan and explicitly reports that no workspace mutation happened.

## Vibe-code a local workspace

Point VA3LM at a project:

```bash
export VA3LM_WORKSPACE_ROOT=/absolute/path/to/project
va3lm workspace
```

Run the coding agent read-only first:

```bash
va3lm execute "Inspect this app and tell me what must change to make the build pass"
```

Allow actual edits and allow-listed development commands:

```bash
va3lm execute "Fix the build, run tests, and stop when the local evidence is green" --approve
```

You can also set the workspace explicitly from the CLI:

```bash
va3lm execute "Make this landing page mobile responsive and run its build" \
  --workspace /absolute/path/to/project \
  --approve \
  --max-rounds 6
```

Default executable allow-list:

```text
python python3 pytest ruff bandit node npm npx pnpm yarn git
```

Override it with `VA3LM_ALLOWED_COMMANDS`. Commands are executed as an argument vector with `shell=False`; arbitrary shell programs are not enabled by default. This allow-list reduces the command surface but is not equivalent to process/network/container isolation.

## HTTP coding executor

The API can inspect the configured `VA3LM_WORKSPACE_ROOT` and run the agent loop:

```text
GET  /api/workspace
POST /api/agent/execute
```

Example body:

```json
{
  "text": "Fix the tests and verify them",
  "approved": false,
  "max_rounds": 4
}
```

HTTP mutation requires **both** `approved: true` and:

```bash
export VA3LM_HTTP_MUTATIONS_ENABLED=true
```

This double gate prevents a browser/API caller from silently receiving VA3LM mutation approval. It does not replace operating-system/container isolation for the process that ultimately runs an approved command.

## Evidence states

The coding executor returns explicit states instead of optimistic prose:

- `MODEL_NOT_CONFIGURED`
- `INVALID_MODEL_DECISION`
- `BLOCKED_PENDING_APPROVAL`
- `COMPLETED_NO_RUNTIME_ACTIONS`
- `COMPLETED_WITH_RUNTIME_EVIDENCE`
- `ACTION_BUDGET_EXHAUSTED`

A successful command records command arguments, exit code, duration, stdout, stderr, and timeout state. Failed/nonzero commands become failed evidence. `COMPLETED_WITH_RUNTIME_EVIDENCE` proves that the listed local runtime actions were observed; it does not imply production deployment.

## Capability plane

`va3lm capabilities` currently exposes 14 capability domains. Thirteen are adapted/runtime-backed and one (`create-app`) remains a blueprint. The execution-specific domains are:

- `workspace-execution`
- `structured-agent-loop`

PACK remains an **ALPHA reference**; VA3LM-owned runtime evidence and CI are authoritative for VA3LM claims.

## Existing command deck

```bash
va3lm agents
va3lm capabilities
va3lm ontology
va3lm plan "Build a FastAPI endpoint with tests"
va3lm brain "Refactor this service safely"
va3lm workspace
va3lm execute "Fix the build and run tests" --approve
va3lm federal-intel
va3lm federal-intel --github-only
va3lm tracking
va3lm tracking --sample
va3lm explain "VA3LM ontology workflow"
```

## Ontology status

The coding ontology models `CodingTask`, `AgentRun`, `FileArtifact`, `CodeChange`, `TestRun`, `SecurityFinding`, `Approval`, `Evidence`, `BuildArtifact`, and `ExplainerArtifact`. It deliberately reports:

```text
BLUEPRINT_NOT_LIVE_FOUNDRY
```

That status remains until a real Foundry deployment is configured and verified.

## Geospatial + public-source boundaries

The geospatial layer supports authorized non-identifying asset/event observations, provenance, timestamps, confidence/uncertainty, GeoJSON, and map review. It does not implement covert person tracking, biometric identification, or communications interception.

The RVIA Federal Intel layer is limited to publicly released, lawfully accessible sources for CIA, NSA, NRO, NGA/NGP, and DIA/GDIP references. It does not authorize classified/leaked collection, credential bypass, operational targeting, or evasion of security controls.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/healthz` | health/version |
| GET | `/api/status` | runtime status + explicit claim boundaries |
| GET | `/api/workspace` | configured workspace/runtime status |
| POST | `/api/agent/execute` | bounded coding-agent execution |
| GET | `/api/agents` | agent roster |
| GET | `/api/ontology` | local ontology blueprint |
| GET | `/api/capabilities` | capability manifest |
| POST | `/api/plan` | deterministic workflow plan |
| POST | `/api/brain` | ask configured local model |
| POST | `/api/explain` | explainer output |
| GET | `/api/federal-intel` | public-source catalog |
| GET | `/api/federal-intel/github` | verified official GitHub sources |
| GET | `/api/tracking` | tracking boundary manifest |
| GET | `/api/tracking/sample` | deterministic demo GeoJSON |
| POST | `/api/tracking/geojson` | validate/normalize authorized observations |
| GET | `/tracking-map` | Google Maps demo surface |

## Development and verification

```bash
pytest -q
ruff check src tests
bandit -q -ll -r src
python -m compileall -q src
```

The `VA3LM Big Virginia` GitHub Actions workflow installs the package, runs the full test suite, lint, Bandit, compilation, and capability-manifest checks.
