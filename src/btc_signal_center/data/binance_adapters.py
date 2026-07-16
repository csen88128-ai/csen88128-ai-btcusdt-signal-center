from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

from btc_signal_center.domain.models import Candle, FlowBucket, TimedValue


def parse_mark_price_klines(rows: Iterable[Sequence[Any]]) -> tuple[Candle, ...]:
    return tuple(
        Candle(
            open_time=_timestamp_ms(row[0]),
            close_time=_timestamp_ms(row[6]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
        )
        for row in rows
    )


def parse_trade_kline_flow(rows: Iterable[Sequence[Any]]) -> tuple[FlowBucket, ...]:
    """Convert USDⓈ-M trade klines into exact taker buy/sell base-volume buckets."""

    buckets: list[FlowBucket] = []
    for row in rows:
        total_volume = float(row[5])
        taker_buy_volume = float(row[9])
        taker_sell_volume = max(0.0, total_volume - taker_buy_volume)
        buckets.append(
            FlowBucket(
                start=_timestamp_ms(row[0]),
                end=_timestamp_ms(row[6]),
                buy_volume=taker_buy_volume,
                sell_volume=taker_sell_volume,
            )
        )
    return tuple(buckets)


def parse_open_interest_history(rows: Iterable[dict[str, Any]]) -> tuple[TimedValue, ...]:
    return tuple(
        TimedValue(
            timestamp=_timestamp_ms(row["timestamp"]),
            value=float(row["sumOpenInterest"]),
        )
        for row in rows
    )


def parse_funding_rate_history(rows: Iterable[dict[str, Any]]) -> tuple[TimedValue, ...]:
    return tuple(
        TimedValue(
            timestamp=_timestamp_ms(row["fundingTime"]),
            value=float(row["fundingRate"]),
        )
        for row in rows
    )


def parse_top_trader_position_ratio(
    rows: Iterable[dict[str, Any]],
) -> tuple[TimedValue, ...]:
    return tuple(
        TimedValue(
            timestamp=_timestamp_ms(row["timestamp"]),
            value=float(row["longShortRatio"]),
        )
        for row in rows
    )


def _timestamp_ms(value: Any) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
