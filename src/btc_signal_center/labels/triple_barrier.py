from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isclose
from statistics import median

from btc_signal_center.domain.models import (
    BarrierEvaluation,
    BarrierOutcome,
    BarrierSpec,
    Candle,
    Excursion,
    PathLabel,
    WindowMetrics,
)


@dataclass(frozen=True, slots=True)
class PathLabelPolicy:
    bias_threshold_pct: float = 0.0025
    compression_range_pct: float = 0.0025
    mean_revert_close_pct: float = 0.0010
    meaningful_excursion_pct: float = 0.0015


class InsufficientWindowData(ValueError):
    """Raised when no fully closed candle belongs to the frozen event window."""


def evaluate_triple_barrier(
    candles: Iterable[Candle],
    spec: BarrierSpec,
    *,
    path_policy: PathLabelPolicy | None = None,
) -> BarrierEvaluation:
    """Evaluate a frozen triple barrier without using partial first/last candles.

    A snapshot taken inside a minute cannot safely use that minute's OHLC because part of
    the bar predates the decision. The engine therefore begins at the next complete minute
    and includes only candles closed no later than ``expires_at``.
    """

    policy = path_policy or PathLabelPolicy()
    safe_start = _ceil_to_minute(spec.as_of)
    ordered = sorted(candles, key=lambda item: (item.open_time, item.close_time))
    eligible = [
        candle
        for candle in ordered
        if candle.open_time >= safe_start and candle.close_time <= spec.expires_at
    ]
    if not eligible:
        raise InsufficientWindowData("no fully closed candles inside frozen event window")

    diagnostics: list[str] = []
    if safe_start > spec.as_of:
        diagnostics.append("PARTIAL_FIRST_CANDLE_EXCLUDED")
    if eligible[-1].close_time < spec.expires_at:
        diagnostics.append("PARTIAL_FINAL_CANDLE_EXCLUDED")
    diagnostics.extend(_gap_diagnostics(eligible))

    outcome = BarrierOutcome.TIMEOUT
    touched_at: datetime | None = None
    for candle in eligible:
        touches_up = candle.high >= spec.upper
        touches_down = candle.low <= spec.lower
        if touches_up and touches_down:
            outcome = BarrierOutcome.AMBIGUOUS
            touched_at = candle.close_time
            break
        if touches_up:
            outcome = BarrierOutcome.UP_FIRST
            touched_at = candle.close_time
            break
        if touches_down:
            outcome = BarrierOutcome.DOWN_FIRST
            touched_at = candle.close_time
            break

    high_candle = max(eligible, key=lambda item: item.high)
    low_candle = min(eligible, key=lambda item: item.low)
    cutoff = eligible[-1].close
    reference = spec.reference_price
    high_change = high_candle.high - reference
    low_change = low_candle.low - reference

    long_mfe = Excursion(
        absolute=high_change,
        pct=high_change / reference,
        occurred_at=high_candle.close_time,
    )
    long_mae = Excursion(
        absolute=low_change,
        pct=low_change / reference,
        occurred_at=low_candle.close_time,
    )
    short_mfe = Excursion(
        absolute=-low_change,
        pct=-low_change / reference,
        occurred_at=low_candle.close_time,
    )
    short_mae = Excursion(
        absolute=-high_change,
        pct=-high_change / reference,
        occurred_at=high_candle.close_time,
    )

    covered_seconds = sum(
        (candle.close_time - candle.open_time).total_seconds() for candle in eligible
    )
    metrics = WindowMetrics(
        cutoff_price=cutoff,
        close_return_pct=(cutoff - reference) / reference,
        high_price=high_candle.high,
        low_price=low_candle.low,
        long_mfe=long_mfe,
        long_mae=long_mae,
        short_mfe=short_mfe,
        short_mae=short_mae,
        candles_used=len(eligible),
        first_candle_open=eligible[0].open_time,
        final_candle_close=eligible[-1].close_time,
        covered_seconds=covered_seconds,
        requested_seconds=(spec.expires_at - spec.as_of).total_seconds(),
    )
    path_label = classify_path(outcome, metrics, policy=policy)
    return BarrierEvaluation(
        outcome=outcome,
        path_label=path_label,
        metrics=metrics,
        touched_at=touched_at,
        diagnostics=tuple(diagnostics),
    )


def classify_path(
    outcome: BarrierOutcome,
    metrics: WindowMetrics,
    *,
    policy: PathLabelPolicy | None = None,
) -> PathLabel:
    policy = policy or PathLabelPolicy()
    if outcome is BarrierOutcome.UP_FIRST:
        return PathLabel.UP_BREAK
    if outcome is BarrierOutcome.DOWN_FIRST:
        return PathLabel.DOWN_BREAK
    if outcome is BarrierOutcome.AMBIGUOUS:
        return PathLabel.AMBIGUOUS_BAR

    total_range_pct = (metrics.high_price - metrics.low_price) / metrics.cutoff_price
    close_pct = metrics.close_return_pct
    if total_range_pct <= policy.compression_range_pct:
        return PathLabel.TIMEOUT_COMPRESSION
    if close_pct >= policy.bias_threshold_pct:
        return PathLabel.TIMEOUT_UP_BIAS
    if close_pct <= -policy.bias_threshold_pct:
        return PathLabel.TIMEOUT_DOWN_BIAS

    both_sides_explored = (
        metrics.long_mfe.pct >= policy.meaningful_excursion_pct
        and abs(metrics.long_mae.pct) >= policy.meaningful_excursion_pct
    )
    if abs(close_pct) <= policy.mean_revert_close_pct and both_sides_explored:
        return PathLabel.TIMEOUT_MEAN_REVERT
    return PathLabel.TIMEOUT_UP_BIAS if close_pct > 0 else PathLabel.TIMEOUT_DOWN_BIAS


def _ceil_to_minute(value: datetime) -> datetime:
    floored = value.replace(second=0, microsecond=0)
    if isclose((value - floored).total_seconds(), 0.0, abs_tol=1e-9):
        return floored
    return floored + timedelta(minutes=1)


def _gap_diagnostics(candles: list[Candle]) -> list[str]:
    if len(candles) < 3:
        return []
    durations = [(item.close_time - item.open_time).total_seconds() for item in candles]
    normal_duration = median(durations)
    for previous, current in zip(candles, candles[1:], strict=False):
        gap = (current.open_time - previous.close_time).total_seconds()
        if gap > max(2.0, normal_duration * 0.10):
            return ["PRICE_WINDOW_HAS_GAPS"]
    return []
