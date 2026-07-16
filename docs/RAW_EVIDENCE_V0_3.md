# Raw Evidence Protocol v0.3

## Objective

Capture the public Binance inputs required to reproduce a frozen BTCUSDT shadow event without copying values from a narrative report or silently realigning exchange time buckets.

## Collected sources

The collector is read-only and restricted to `BTCUSDT`:

1. USDⓈ-M mark-price 1-minute klines;
2. USDⓈ-M traded-price 1-minute klines;
3. 5-minute open-interest history;
4. funding-rate history;
5. 5-minute top-trader position long/short ratio.

No account, balance, order, position-management or execution endpoint exists in this client.

## Immutability

Every HTTP response is stored byte-for-byte under `payloads/`. The append-only `manifest.jsonl` records:

- provider and endpoint;
- complete public query parameters;
- request URL;
- receive timestamp;
- HTTP status;
- payload byte length;
- SHA-256 digest;
- relative payload path.

An existing payload path cannot be overwritten with different bytes.

## Event-window alignment

### Price and taker flow

Mark-price and traded-price 1-minute klines permit the same as-of-safe window policy used by `shadow_v0.2`:

- exclude the minute containing a mid-minute decision timestamp;
- use only fully closed candles;
- exclude a final minute that closes after the frozen horizon.

For traded-price klines:

```text
taker_sell_base_volume = total_base_volume - taker_buy_base_volume
```

This reconstructs taker flow for the exact set of safe 1-minute event buckets.

### OI and trader ratios

OI and top-trader ratios are lower-frequency observations. They must not be presented as exact continuous-window totals. Reports must retain source timestamps and disclose distance from the frozen start/end boundaries.

### Funding

Funding is event-based. A window with no funding timestamp inside it records no new funding event; it must not infer a continuous change from mark price.

## CLI

```bash
btc-shadow-replay collect-binance \
  --symbol BTCUSDT \
  --start 2026-07-16T03:14:08+08:00 \
  --end 2026-07-16T11:14:08+08:00 \
  --output data/raw/2026-07-16T031408+0800
```

The command prints a collection report. Raw payloads remain local and are ignored by Git; evidence summaries and hashes may be promoted only after validation.

## Production boundary

Raw collection does not grant trading permission. Calibration, effective sample size, drift, execution cost and positive net-EV lower-bound gates remain mandatory. All outputs are research records, not trading advice.
