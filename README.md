# Bhaskar Trade Terminal V3 — Sprint 1

This development build introduces:

- modular backend architecture;
- robust Dhan option-chain response normalization;
- normalized live option contracts;
- strike viability endpoint;
- required exit premium and NIFTY movement;
- liquidity, spread, Delta, Gamma and OI scoring;
- nearby better-strike suggestion;
- first V3 dashboard;
- tests for parsing and viability calculations.

## Use only on `v3-dev`

Do not upload this package into `main` yet.

## Deployment test

Create a separate Render service or Preview Environment pointing to `v3-dev`.
Do not switch the current production service away from `main`.

## API

`POST /api/viability`

Example:

```json
{
  "expiry": "2026-08-04",
  "strike": 24300,
  "side": "ce",
  "lots": 4,
  "target_net_profit": 5000,
  "entry_price": 106.10,
  "charge_buffer": 150,
  "expected_range_remaining": 80
}
```

## Current scope

The verdict currently uses:

- Delta
- Gamma
- bid/ask spread
- OI and OI change
- volume
- required NIFTY move
- optional expected remaining range

The full NIFTY breadth, VIX, chart structure, global macro and news framework will be added in later sprints.
