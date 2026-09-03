# THE BLACK HOUSE // AUTHORIZED CYBER LAB POLICY

## Mission

The Black House cyber-learning layer converts public security training into reproducible defensive skills without treating offensive capability as unrestricted authority.

## Scope contract

Every active exercise must have a declared target scope before execution. Valid targets are limited to:

- localhost;
- disposable virtual machines owned by the operator;
- containers created specifically for the exercise;
- intentionally vulnerable training targets;
- packet captures supplied for analysis;
- wireless equipment and clients owned by the operator and isolated from third parties.

No target is authorized merely because it is reachable.

## Action states

### ALLOW

Read-only host inspection, local Linux practice, package-management practice, packet analysis, defensive configuration review, service discovery against declared lab targets, log analysis, threat detection, and mitigation documentation.

### REVIEW

Actions that can interrupt availability, recover credentials, alter network state, or capture traffic require an explicit isolated-lab scope record before execution.

### BLOCK

Third-party targeting, uncontrolled deauthentication, credential theft, persistence, destructive actions, stealth against non-lab systems, secret collection, or attempts to bypass an authorization boundary.

## Evidence contract

Each lab result must preserve:

1. scope;
2. objective;
3. commands or tools used;
4. observable output;
5. finding;
6. defensive significance;
7. mitigation;
8. cleanup state.

## Learning rule

A technique is not considered learned because a command ran successfully. Black House requires an explanation of what happened, why it happened, what evidence proves it, how defenders detect it, and how the risk is reduced.
