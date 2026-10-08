# Third-Party Catalog Sources

## Open Source Everything

- Upstream project: Open Source Everything
- Author/maintainer: An-anonymous-coder
- Canonical host identified by upstream: https://gitlab.com/an-anonymous-coder1/Open-Source-Everything
- GitHub mirror: https://github.com/An-anonymous-coder/Open-Source-Everything
- Integrated snapshot: release 165.2026.5.13.0
- Git commit: 7290f2cb9ffa7c7bba1723b7e06f726802de51be
- Upstream license: GNU GPL v3

Shaggoth does not vendor or relicense the upstream catalog. The adapter fetches the
upstream README at runtime and generates a local derived index containing names,
links, and category metadata with source provenance. Generated catalog caches live
under `runtime/` or the configured temporary cache path and are not committed to
this MIT-licensed repository.

Users redistributing upstream-derived catalog data should review and comply with
the upstream GPLv3 license.
