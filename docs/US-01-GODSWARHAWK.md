# US-01-GoDsWarHawk

US-01-GoDsWarHawk is a GPT-Doug software-agent swarm profile. The name is a
project codename only and does not represent U.S. government designation,
endorsement, or affiliation.

## Mission

Coordinate bounded workers for software engineering, ontology/research
analysis, defensive review, verification, and operator handoff.

Workers:

- command: scope and acceptance criteria
- cartographer: authorized context and dependency mapping
- builder: minimal compatible implementation plan
- guardian: safety/security/privacy review
- verifier: tests, invariants, and proof requirements
- comms: provenance and human-decision handoff

The default is dry-run. Live worker execution requires an explicit local gate:

~~~bash
export GPT_DOUG_WARHAWK_EXECUTE=1
~~~

## CLI

~~~bash
gpt-doug warhawk status
gpt-doug warhawk plan "audit this repo and propose the smallest safe fix" --repo .
GPT_DOUG_WARHAWK_EXECUTE=1 gpt-doug warhawk run "review this repo and produce a verified implementation plan" --repo . --workers 6 --execute
~~~

The live mode invokes GPT-Doug Brain workers. It does not automatically mutate
the repository or send external messages. Those actions remain separate,
explicitly approved operations.

## Hard boundaries

The profile blocks autonomous target selection, weapons release, weapon/drone
swarm control, hostile engagement, critical-infrastructure disruption,
hack-back, credential theft, unattended real-world vehicle commands, and
bypassing human authorization.
