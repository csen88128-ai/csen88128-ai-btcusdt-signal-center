# Shadow Replay Protocol v0.2

## Purpose

Convert every frozen BTCUSDT shadow decision into a reproducible evidence record. The replay engine evaluates what happened without changing the original horizon, barriers, action or decision-time information.

## Frozen fields

Each event must freeze:

- `symbol`;
- `as_of` and timezone;
- reference price;
- upper/lower barriers;
- horizon expiry;
- original action;
- model, feature, calibration and policy versions;
- original scenario weights, explicitly marked calibrated or uncalibrated.

Changing a frozen field creates a new experiment; it must never overwrite the original event.

## Price-window policy

1. Use 1-minute closed candles.
2. If `as_of` is inside a minute, exclude that minute because its OHLC contains pre-decision data.
3. Exclude any candle closing after the frozen expiry.
4. Scan candles chronologically.
5. If both barriers appear inside the same 1-minute candle, return `AMBIGUOUS`; do not infer intrabar order.
6. Report price coverage and data gaps.

## Primary labels

- `UP_FIRST`
- `DOWN_FIRST`
- `TIMEOUT`
- `AMBIGUOUS`

## Path sub-labels

A primary `TIMEOUT` label is supplemented by one of:

- `TIMEOUT_UP_BIAS`
- `TIMEOUT_DOWN_BIAS`
- `TIMEOUT_MEAN_REVERT`
- `TIMEOUT_COMPRESSION`

The sub-label does not replace the primary triple-barrier label.

## Excursion metrics

For every event, record:

- cutoff return;
- high and low;
- long MFE and MAE;
- short MFE and MAE;
- occurrence times;
- price-window coverage.

## Derivative alignment

Exchange natural-time buckets generally do not align with event time. v0.2 includes only buckets fully contained in the frozen window and reports coverage. Partial buckets are never silently prorated. Future versions may use raw trades or higher-resolution source data for exact reconstruction.

## Gate interpretation

A timeout or ambiguous result is evidence that a barrier-level directional edge was not demonstrated in that event. It does not prove that every rejected trade would have lost.

`LIGHT_LONG` or `LIGHT_SHORT` remains blocked unless all of the following are available:

- calibrated probability;
- sufficient effective sample size;
- positive net-EV lower bound;
- passing data, structure, regime, predictability, execution and risk gates.

## Current project restrictions

- BTCUSDT only;
- no automatic order placement;
- no live capital exploration;
- no ETH, news or on-chain expansion;
- no Kelly sizing;
- no online automatic weight updates.

All records are for research and system validation, not trading advice.
