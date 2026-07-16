from datetime import datetime, timedelta, timezone

from btc_signal_center.domain.models import BarrierOutcome, BarrierSpec, Candle, PathLabel
from btc_signal_center.labels.triple_barrier import evaluate_triple_barrier

UTC = timezone.utc


def candle(minute: int, *, high: float, low: float, close: float) -> Candle:
    start = datetime(2026, 7, 16, 3, minute, tzinfo=UTC)
    return Candle(
        open_time=start,
        close_time=start + timedelta(minutes=1),
        open=100.0,
        high=high,
        low=low,
        close=close,
    )


def spec(minutes: int = 30) -> BarrierSpec:
    return BarrierSpec(
        as_of=datetime(2026, 7, 16, 3, 14, 8, tzinfo=UTC),
        expires_at=datetime(2026, 7, 16, 3, 14, 8, tzinfo=UTC) + timedelta(minutes=minutes),
        reference_price=100.0,
        upper=102.0,
        lower=98.0,
    )


def test_excludes_partial_first_minute_and_labels_timeout_mean_revert() -> None:
    candles = [
        candle(14, high=103.0, low=97.0, close=100.0),  # unsafe partial minute
        candle(15, high=100.7, low=99.0, close=99.4),
        candle(16, high=101.0, low=98.9, close=100.02),
    ]

    result = evaluate_triple_barrier(candles, spec())

    assert result.outcome is BarrierOutcome.TIMEOUT
    assert result.path_label is PathLabel.TIMEOUT_MEAN_REVERT
    assert result.metrics.candles_used == 2
    assert result.metrics.high_price == 101.0
    assert "PARTIAL_FIRST_CANDLE_EXCLUDED" in result.diagnostics


def test_returns_first_barrier_touch() -> None:
    candles = [
        candle(15, high=101.0, low=99.0, close=100.5),
        candle(16, high=102.1, low=99.8, close=101.8),
        candle(17, high=101.0, low=97.5, close=98.0),
    ]

    result = evaluate_triple_barrier(candles, spec())

    assert result.outcome is BarrierOutcome.UP_FIRST
    assert result.path_label is PathLabel.UP_BREAK
    assert result.touched_at == datetime(2026, 7, 16, 3, 17, tzinfo=UTC)


def test_same_candle_touch_is_ambiguous() -> None:
    result = evaluate_triple_barrier(
        [candle(15, high=102.5, low=97.5, close=100.0)],
        spec(),
    )

    assert result.outcome is BarrierOutcome.AMBIGUOUS
    assert result.path_label is PathLabel.AMBIGUOUS_BAR
