# GLASS ONION SCALE — Music and Banking Service Shield (CL1)

**Status:** an implementation branch for the GPT-DOUG ecosystem, not a connected-bank monitoring service, OAuth client, third-party firewall, or assurance that a music provider's or bank's infrastructure has been secured.

## Trust architecture

    USER / OPERATOR (Mac)
           |
    GPT-DOUG / CL1
           |
    KRAKEN SHIELD
           |
    GLASS ONION SERVICE POLICY
       /                \
    MUSIC             BANKING
    Public links      No connected bank adapters
    Allowlist         Read/write actions blocked
       \                /
         PRIVATE HASH-LINKED DECISION AUDIT

Glass Onion retains its existing role as an evidence/provenance layer and the existing private-vault implementation remains separate. This PR does not unlock the private vault, change macOS Keychain credentials or collect banking information.

## Music sector

The local registry includes YouTube, YouTube Music, SoundCloud, Spotify, Apple Music, Bandcamp, Audius, Jamendo, Internet Archive, Suno, DistroKid, Tidal and Deezer. They are policy targets, **not verified account integrations**.

Only public music-link viewing is allowed for reviewed HTTPS hosts. Reject alternate hosts, lookalikes, embedded passwords, unsafe schemes, unexpected ports and sensitive query strings. Account changes, uploads, royalties, payments and payouts remain blocked.

Both source and GitHub Pages builds of ZYRA Jukebox use a browser-side Glass Onion check on their built-in search links, Archive lookups, and YouTube/SoundCloud embed operations. A browser-side check cannot stop later redirects, compromised sites, independent radio streams, unmediated external integrations, or malicious browser extensions. These limitations need a future server/network enforcement layer.

## Banking sector

**No bank accounts were connected, scanned, modified or accessed.** The only allowed operations are local inventory/status/policy inspection, with no financial data. Balance queries, transaction retrieval, payee changes, transfers, bill payments, exports, credentials and OAuth are denied until a separately reviewed, user-authorized, verified read-only connector is built.

Future bank connections need: explicit user authorization, provider-side MFA, minimal permissions, consent revocation, dedicated secret storage, no banking data in public repos or AI prompts, and a separate audit and recovery plan. Never treat a model-generated approval as account authorization.

## Privacy / audit

- No credentials, account numbers, music copyrights metadata, customer lists or URLs are stored by the new service policy.
- The audit stores only a coarse policy fingerprint, decision, reason code, timestamp and hash-chain link.
- A broken audit, remote AI routing or latched Kraken emergency stop blocks requests.
- The hash chain can show modification of retained entries; it is not proof against deletion/truncation of the whole file.
- No paid API, financial action, music publication or cloud deployment is performed by this PR.

## CLI (local Mac, after checking out branch)

    cd ~/gpt-doug-cl1
    .venv/bin/python -m kraken_shield services
    printf '%s' 'https://soundcloud.com/search?q=music' | .venv/bin/python -m kraken_shield service-check --sector music --service soundcloud --operation open_public_link
    .venv/bin/python -m kraken_shield service-check --sector bank --service bank --operation transfer </dev/null
    .venv/bin/python -m kraken_shield verify

The bank transfer check is expected to return BLOCK (exit code 3) and cannot initiate transfers. Do not enter banking data in the terminal command.

## Validation

    python3 -m unittest discover -s tests -p 'test_glass_onion_service_shield.py' -v
    node --test apps/zyra-jukebox/glass-onion-shield.test.cjs

The Glass Onion Service Shield Gate runs these checks with no API credentials or live accounts.

## Scope status

- Kraken Shield service audit and local policy: **implemented in PR**.
- Jukebox built-in source links and embeds: **guarded in PR, client-side only**.
- Spotify, Apple Music, Suno, DistroKid and others: **catalogued, not connected**.
- Banking: **default-deny policy, no authenticated integration**.
- Existing Glass Onion private vault: **unchanged**.
- Live bank and third-party account protection: **not implemented**.

Review, merge, and deploy are separate operator decisions. A GitHub PR alone does not change provider settings or secure any connected bank accounts.
