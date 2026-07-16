from datetime import datetime, timedelta, timezone

from btc_signal_center.domain.models import FlowBucket, TimedValue
from btc_signal_center.features.event_window import aggregate_full_flow_buckets, endpoint_change

UTC = timezone.utc
BASE = datetime(2026, 7, 16, 3, 14, 8, tzinfo=UTC)


def test_aggregate_excludes_partial_exchange_buckets_and_reports_coverage() -> None:
    buckets = [
        FlowBucket(BASE - timedelta(minutes=4), BASE + timedelta(minutes=1), 10, 20),
        FlowBucket(BASE + timedelta(minutes=1), BASE + timedelta(minutes=6), 30, 20),
        FlowBucket(BASE + timedelta(minutes=6), BASE + timedelta(minutes=11), 20, 10),
        FlowBucket(BASE + timedelta(minutes=26), BASE + timedelta(minutes=31), 50, 1),
    ]

    result = aggregate_full_flow_buckets(
        buckets,
        start=BASE,
        end=BASE + timedelta(minutes=30),
    )

    assert result.buckets_used == 2
    assert result.buy_volume == 50
    assert result.sell_volume == 30
    assert result.delta == 20
    assert result.buy_sell_ratio == 50 / 30
    assert result.coverage_ratio == 1 / 3


def test_endpoint_change_uses_first_and_last_points_inside_window() -> None:
    points = [
        TimedValue(BASE - timedelta(minutes=1), 100),
        TimedValue(BASE + timedelta(minutes=1), 105),
        TimedValue(BASE + timedelta(minutes=10), 110),
        TimedValue(BASE + timedelta(minutes=31), 90),
    ]

    result = endpoint_change(points, start=BASE, end=BASE + timedelta(minutes=30))

    assert result.start_value == 105
    assert result.end_value == 110
    assert result.absolute_change == 5
    assert result.pct_change == 5 / 105
