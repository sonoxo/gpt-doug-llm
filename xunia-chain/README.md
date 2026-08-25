# XUNIA Chain v1

XUNIA Chain is a self-contained local/private-cloud blockchain with native coin **XUN**.

## Network parameters

- Chain ID: `xunia-main-v1`
- Native symbol: `XUN`
- Atomic units: 100,000,000 per XUN
- Max issuance: 500,000,000 XUN
- Initial block reward: 1,000 XUN
- Halving interval: 210,000 blocks
- Consensus: SHA-256 proof of work (local-dev difficulty is configurable)
- Transaction signatures: Ed25519
- Address format: `xun_` + 40 hex characters derived from the public key
- Default node port: `4317`
- Persistent chain: `.xunia/chain.json`

## Build

```bash
cd xunia-chain
npm install
npm run build
npm test
```

## Create a wallet

```bash
npm run wallet
```

The private key is stored in `.xunia/wallet.json` with owner-only file permissions. Back it up securely. Never commit it.

## Mine XUN

```bash
npm run mine -- 2
npm run balance
```

Difficulty `1` or `2` is appropriate for local development. Higher values require more work.

## Start a node

```bash
npm start
```

Open `http://127.0.0.1:4317/` for the built-in explorer summary.

API:

- `GET /health`
- `GET /chain`
- `GET /balance/:address`
- `POST /tx`
- `POST /mine` with `{ "miner": "xun_...", "difficulty": 2 }`

## Signed payment example

Wallets sign the canonical transaction payload with Ed25519. Nodes independently verify that the supplied public key derives the sender address, the transaction ID matches, the signature is valid, the nonce is exact, and the account has enough XUN for amount + fee.

## SONOXO integration

Set:

```bash
SONOXO_TELEMETRY=1
SONOXO_URL=http://127.0.0.1:3001/api/sonoxo/harvest
```

Accepted transactions and mined blocks emit non-consensus telemetry to SONOXO. Telemetry failure never affects chain validity.

## Docker

```bash
docker build -t xunia-chain .
docker run --rm -p 4317:4317 -e XUNIA_PORT=4317 -v xunia-data:/app/.xunia xunia-chain
```

## Security properties

- no arbitrary mint transaction
- issuance only through validated block rewards
- capped total issuance
- replay protection through account nonces
- Ed25519 transaction authentication
- deterministic chain replay validation
- proof-of-work checked for every non-genesis block
- block-link and block-hash integrity checks
- private wallet file permission hardening
- graceful SIGTERM/SIGINT shutdown

## Scope

This repository contains a complete **local/private-cloud v1 chain implementation** suitable for development, integration testing, demonstrations, and controlled XUNIA deployments. Public permissionless production deployment would additionally require adversarial consensus testing, P2P networking/peer discovery, DoS protections, independent security review, operational key management, upgrade governance, and jurisdiction-specific launch review.
