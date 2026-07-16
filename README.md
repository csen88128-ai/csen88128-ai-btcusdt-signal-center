# BTCUSDT Signal Calibration Center

Clean rebuild of the BTCUSDT research system. The repository is intentionally limited to:

- BTCUSDT only;
- research, replay and shadow validation;
- no automatic order placement;
- no ETH expansion, news agents, on-chain agents, Kelly sizing or online self-adjusting weights.

## Current milestone: `shadow_v0.2`

The first production-shaped slice implements:

1. closed-candle, as-of-safe triple-barrier replay;
2. `UP_FIRST / DOWN_FIRST / TIMEOUT / AMBIGUOUS` labels;
3. path sub-labels for timeout events;
4. long/short MFE and MAE with occurrence times;
5. exact-window coverage reporting for derivative buckets;
6. append-only JSONL evidence records;
7. tests and CI.

This milestone does **not** produce calibrated trading probabilities. Missing calibration or value evidence must keep the action at `OBSERVE` or `REJECT`.

## Quick start

```bash
python -m pip install -e '.[dev]'
pytest
```

Replay a JSON payload:

```bash
btc-shadow-replay replay --input examples/replay_input.json
```

The input timestamps must be timezone-aware ISO-8601 values. The engine excludes a partially formed first minute and includes only candles whose close time is not later than the frozen horizon.

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
