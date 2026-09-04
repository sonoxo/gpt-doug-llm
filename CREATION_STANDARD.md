# XUNIA Creation Standard — Browser-First / Free-Access

This repository treats public accessibility as a build requirement for interactive creations.

## Required defaults

1. **Free browser page first.** Every interactive tool, plugin, simulator, dashboard, visualization, launcher, training surface, or public resource MUST expose a free browser-accessible page when the capability can run safely on the web.
2. **Catalog every interactive creation.** Add or update its entry in `docs/resources.json` in the same change that introduces the creation.
3. **Local is a companion, not the only door.** A local/admin build MAY exist for development, offline use, privileged controls, local hardware, filesystem access, or secrets. If browser delivery is technically impossible, the catalog entry MUST use `access: "local-required"` and include `localOnlyReason`.
4. **Zero-cost baseline.** The baseline public experience MUST prefer open data, public APIs, free tiers, free-registration providers, static assets, browser compute, or self-hosted components. Paid services may enhance the experience but MUST NOT be required for the baseline unless explicitly documented.
5. **No secrets in the browser or repository.** API secrets, tokens, private credentials, and privileged Black House controls MUST remain server-side/local/admin-only.
6. **Provenance and licenses stay visible.** Third-party projects, datasets, APIs, and open-source components retain their attribution, license, and provider terms.
7. **Beginner-accessible launch.** Each creation should provide a clear `Open` action for public web use and, when applicable, a one-command local/admin launcher.
8. **Health and failure states.** Interactive pages must show useful loading/error/offline states instead of silently failing.
9. **Responsive by default.** Public interfaces must support desktop and mobile browsers unless the capability itself requires a larger screen.
10. **CI enforcement.** The GitHub Pages workflow validates the Resource Hub and its registry so the catalog is part of the release surface.

## Canonical public directory

- Human interface: `docs/resources.html`
- Machine-readable registry: `docs/resources.json`
- Public URL: `https://sonoxo.github.io/gpt-doug-llm/resources.html`

## Access labels

- `public` — opens directly in a browser with no local install.
- `free-registration` — browser-accessible, but the provider may require a free account/key.
- `free-tier` — provider offers a no-cost tier; limits/terms can change.
- `local-ready` — local launcher exists while public hosting is being prepared.
- `local-required` — local execution is technically required; `localOnlyReason` is mandatory.

This standard is repository policy. New interactive work should extend the public hub rather than creating isolated, undiscoverable tools.
