# GPT-DOUG Market Intelligence Terminal

A free, read-only Bloomberg-style research dashboard built from public market data, RSS and SEC EDGAR. It has no brokerage connection, no paid API keys and no trade execution.

## Run locally

```bash
python3 market-terminal/scripts/collect_market_data.py
python3 -m http.server 8080
```

Open `http://localhost:8080/market-terminal/`.

## Data design

- Quotes and one-month chart history: Yahoo Finance public chart endpoint (delayed; availability not guaranteed)
- Company filings: SEC EDGAR primary-source submissions
- Catalysts: public RSS feeds
- Refresh: GitHub Actions every 30 minutes on weekdays, plus manual dispatch
- Resilience: the UI loads a safe bundled fallback if the snapshot is missing
- Privacy: watchlists stay in browser local storage

The “DOUG COMMAND” box is an offline command parser, so it consumes no LLM tokens. An optional local-model adapter can be added later without changing the data layer.

## Limits

This is not the Bloomberg Terminal and does not include Bloomberg’s proprietary data, analytics or execution network. Public feeds may be delayed, revised, rate-limited or unavailable. This software is for research and education only and is not investment advice.
