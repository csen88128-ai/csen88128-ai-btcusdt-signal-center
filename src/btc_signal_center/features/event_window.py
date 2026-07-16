from __future__ import annotations

from datetime import datetime
from typing import Iterable

from btc_signal_center.domain.models import FlowAggregate, FlowBucket, SeriesChange, TimedValue


def aggregate_full_flow_buckets(
    buckets: Iterable[FlowBucket],
    *,
    start: datetime,
    end: datetime,
) -> FlowAggregate:
    """Aggregate only buckets fully contained in the event window.

    Partially overlapping exchange buckets are excluded rather than proportionally allocated.
    The returned coverage ratio makes that information loss explicit.
    """

    _validate_window(start, end)
    selected = sorted(
        (bucket for bucket in buckets if bucket.start >= start and bucket.end <= end),
        key=lambda item: item.start,
    )
    buy = sum(item.buy_volume for item in selected)
    sell = sum(item.sell_volume for item in selected)
    covered = sum((item.end - item.start).total_seconds() for item in selected)
    ratio = None if sell == 0 else buy / sell
    return FlowAggregate(
        buy_volume=buy,
        sell_volume=sell,
        delta=buy - sell,
        buy_sell_ratio=ratio,
        covered_seconds=covered,
        requested_seconds=(end - start).total_seconds(),
        buckets_used=len(selected),
    )


def endpoint_change(
    points: Iterable[TimedValue],
    *,
    start: datetime,
    end: datetime,
) -> SeriesChange:
    """Use the first point at/after start and the last point at/before end."""

    _validate_window(start, end)
    ordered = sorted(points, key=lambda item: item.timestamp)
    start_candidates = [item for item in ordered if item.timestamp >= start and item.timestamp <= end]
    end_candidates = [item for item in ordered if item.timestamp <= end and item.timestamp >= start]
    if not start_candidates or not end_candidates:
        return SeriesChange(None, None, None, None, None, None)

    first = start_candidates[0]
    last = end_candidates[-1]
    absolute = last.value - first.value
    pct = None if first.value == 0 else absolute / first.value
    return SeriesChange(
        start_value=first.value,
        end_value=last.value,
        absolute_change=absolute,
        pct_change=pct,
        start_time=first.timestamp,
        end_time=last.timestamp,
    )


def _validate_window(start: datetime, end: datetime) -> None:
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("start must be timezone-aware")
    if end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("end must be timezone-aware")
    if end <= start:
        raise ValueError("end must be later than start")
