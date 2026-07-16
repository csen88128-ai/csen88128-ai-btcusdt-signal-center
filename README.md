# BTCUSDT Signal Calibration Center

Clean rebuild of the BTCUSDT research system. The repository is intentionally limited to:

- BTCUSDT only;
- research, replay and shadow validation;
- no automatic order placement;
- no ETH expansion, news agents, on-chain agents, Kelly sizing or online self-adjusting weights.

## Current milestone: `raw_evidence_v0.3`

The merged foundation now implements:

1. closed-candle, as-of-safe triple-barrier replay;
2. `UP_FIRST / DOWN_FIRST / TIMEOUT / AMBIGUOUS` labels;
3. path sub-labels for timeout events;
4. long/short MFE and MAE with occurrence times;
5. exact-window coverage reporting for derivative buckets;
6. append-only JSONL decision evidence;
7. read-only Binance public market collection;
8. byte-preserving raw payload storage with SHA-256 and append-only manifests;
9. exact 1-minute taker buy/sell reconstruction from traded klines;
10. tests and CI.

These milestones do **not** produce calibrated trading probabilities. Missing calibration or value evidence must keep the action at `OBSERVE` or `REJECT`.

## First verified shadow evidence

The repository includes the price-verified replay summary for the BTCUSDT event frozen at `2026-07-16T03:14:08+08:00`:

```text
evidence/shadow/2026-07-16T031408+0800_BTCUSDT_summary.json
```

Its 30-minute, 2-hour and 8-hour primary labels are all `TIMEOUT`, while path sub-labels preserve the materially different trajectories. The record remains `FINALIZED_PRICE_ONLY`; derivative figures are not promoted until their raw payloads and exact alignment are verified.

## Quick start

```bash
python -m pip install -e '.[dev]'
pytest
```

Replay a JSON payload:

```bash
btc-shadow-replay replay --input examples/replay_input.json
```

Collect an immutable Binance public evidence bundle:

```bash
btc-shadow-replay collect-binance \
  --symbol BTCUSDT \
  --start 2026-07-16T03:14:08+08:00 \
  --end 2026-07-16T11:14:08+08:00 \
  --output data/raw/2026-07-16T031408+0800
```

Raw payloads are stored locally and ignored by Git. Their manifest records source endpoints, query parameters, receive timestamps, byte lengths and SHA-256 digests. The replay engine excludes a partially formed first minute and includes only candles whose close time is not later than the frozen horizon.

## Decision doctrine

```text
structure valid
+ conditional uncertainty reduced
+ calibrated probability available
+ state stable
+ net EV lower bound positive
= eligible for LIGHT review

otherwise = OBSERVE / REJECT
```

All outputs are research records, not trading advice.
