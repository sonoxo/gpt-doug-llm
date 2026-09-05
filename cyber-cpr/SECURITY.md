# Cyber CPR Security Policy

Cyber CPR is defensive, local-first DevSecOps software.

## Supported version

Current supported release: **0.1.x**.

## Trust boundary

Cyber CPR reads GitHub Actions state through an already-authenticated local `gh` CLI session. It does not embed or persist GitHub tokens.

Automatic remediation is **off by default**. When enabled, a repair must be an exact user-defined command in `config.json`, match an exact workflow name, and execute inside an explicit local Git repository working tree.

Cyber CPR must not automatically change secrets, production credentials, repository or organization permissions, branch protection, cloud IAM, production databases, user data, firewall policy, authentication policy, or unrelated application logic.

## Reporting vulnerabilities

Do not include live credentials, tokens, private keys, or private infrastructure details in a public issue. Report only the minimum reproducible technical details needed to describe the problem.

## Authorized use

Use Cyber CPR only on repositories and systems you own or are authorized to administer.
