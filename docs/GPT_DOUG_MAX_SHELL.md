# GPT-Doug MAX Agentic Terminal

`gpt_doug_max.py` composes the repository's existing brain/runtime/data layers into one operator shell without replacing their individual safety boundaries.

## Architecture

```text
human keyboard / optional local mic
              |
              v
       GPT-Doug MAX shell
              |
    +---------+-----------+----------------+
    |         |           |                |
    v         v           v                v
 llm_backend  XUNIA      ZYRA          Palantir
 provider     local RAG   bounded agent   ontology/data
 router       + Ollama    repo actions    grounding
    |         |           |                |
    +---------+-----------+----------------+
              |
              v
          state bus
 ~/.gpt-doug/max-shell-state.json
              |
              v
        live terminal skin
```

The state bus decouples input from visual rendering. This is deliberate: the old single-PTY renderer and command editor could fight over the same terminal buffer, causing ghost frames, broken backspace behavior and Ctrl-C handoff problems.

## Run

```bash
python3 gpt_doug_max.py
```

or:

```bash
zsh scripts/gptdoug-max
```

For the animated skin plus shell in one Terminal window, install `tmux` and run:

```bash
brew install tmux
zsh scripts/gptdoug-max-ui
```

The visual pane targets 60 frames/second, but actual paint rate is limited by Terminal, machine load and portrait size.

## Commands

- `/status` - system, Git, provider and visual state.
- `/brain` - provider health.
- `/xunia <prompt>` - local GPT-XUNIA-GODIS prompt.
- `/rag <question>` - repository-grounded local answer.
- `/agent <goal>` - bounded ZYRA coding mission. Requires `/arm` and confirmation.
- `/agents` - installed agent surfaces.
- `/swarm [demo|file.json]` - bounded revenue swarm. Produces drafts only.
- `/palantir <command>` - existing Palantir terminal surface. Writes remain approval gated.
- `/github` - local Git/GitHub status.
- `/test [targets]` - pytest.
- `/build [command]` - explicit build command; armed only.
- `/deploy [command]` - explicit configured deployment; armed only.
- `/voice on|off` - macOS speech synthesis.
- `/listen [seconds]` - optional local microphone transcription.
- `/joke` - brain-generated short joke.
- `/power` - visual POWER state + spoken acknowledgement.
- `/arm [seconds]` / `/disarm` - short-lived mutation authority.
- `$ <command>` - explicit shell execution. Mutations require arm + confirmation.
- `/kill` or `/quit` - clean exit.

Plain English goes to the configured `agents.llm_backend` provider and is never silently executed as a shell command.

## Optional microphone stack

Voice output uses the macOS `say` command and needs no Python package. Local speech-to-text is opt-in:

```bash
python3 -m pip install sounddevice numpy faster-whisper
```

`/listen 5` records five seconds locally and transcribes it with faster-whisper. No cloud speech API is selected by this code path.

## Provider setup

The shell uses the existing provider facade. For local XUNIA/Ollama:

```bash
export GPT_DOUG_PROVIDER=ollama
export OLLAMA_MODEL=gpt-xunia-brain
```

For the multi-provider XUNIA consensus router:

```bash
export GPT_DOUG_PROVIDER=xunia
```

Provider credentials and tenant permissions remain external configuration and are not stored by the MAX shell.

## Safety / authority

- Natural language is not auto-executed.
- Read-only shell commands may run directly with a `$` prefix.
- Mutating shell commands require `/arm` plus a second confirmation.
- ZYRA coding missions retain the existing repository-bounded agent restrictions.
- Palantir writes retain the existing approval callback.
- Revenue swarm remains draft-only and does not send outreach or move money.
- `/deploy` does nothing unless an explicit deployment command is configured or supplied.
