from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class BarrierOutcome(StrEnum):
    UP_FIRST = "UP_FIRST"
    DOWN_FIRST = "DOWN_FIRST"
    TIMEOUT = "TIMEOUT"
    AMBIGUOUS = "AMBIGUOUS"


class PathLabel(StrEnum):
    UP_BREAK = "UP_BREAK"
    DOWN_BREAK = "DOWN_BREAK"
    AMBIGUOUS_BAR = "AMBIGUOUS_BAR"
    TIMEOUT_UP_BIAS = "TIMEOUT_UP_BIAS"
    TIMEOUT_DOWN_BIAS = "TIMEOUT_DOWN_BIAS"
    TIMEOUT_MEAN_REVERT = "TIMEOUT_MEAN_REVERT"
    TIMEOUT_COMPRESSION = "TIMEOUT_COMPRESSION"


@dataclass(frozen=True, slots=True)
class Candle:
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        _require_aware(self.open_time, "open_time")
        _require_aware(self.close_time, "close_time")
        if self.close_time <= self.open_time:
            raise ValueError("close_time must be later than open_time")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low is inconsistent with OHLC values")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high is inconsistent with OHLC values")


@dataclass(frozen=True, slots=True)
class BarrierSpec:
    as_of: datetime
    expires_at: datetime
    reference_price: float
    upper: float
    lower: float

    def __post_init__(self) -> None:
        _require_aware(self.as_of, "as_of")
        _require_aware(self.expires_at, "expires_at")
        if self.expires_at <= self.as_of:
            raise ValueError("expires_at must be later than as_of")
        if not self.lower < self.reference_price < self.upper:
            raise ValueError("barriers must satisfy lower < reference_price < upper")


@dataclass(frozen=True, slots=True)
class Excursion:
    absolute: float
    pct: float
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class WindowMetrics:
    cutoff_price: float
    close_return_pct: float
    high_price: float
    low_price: float
    long_mfe: Excursion
    long_mae: Excursion
    short_mfe: Excursion
    short_mae: Excursion
    candles_used: int
    first_candle_open: datetime
    final_candle_close: datetime
    covered_seconds: float
    requested_seconds: float

    @property
    def price_coverage_ratio(self) -> float:
        if self.requested_seconds <= 0:
            return 0.0
        return min(1.0, self.covered_seconds / self.requested_seconds)


@dataclass(frozen=True, slots=True)
class BarrierEvaluation:
    outcome: BarrierOutcome
    path_label: PathLabel
    metrics: WindowMetrics
    touched_at: datetime | None = None
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TimedValue:
    timestamp: datetime
    value: float

    def __post_init__(self) -> None:
        _require_aware(self.timestamp, "timestamp")


@dataclass(frozen=True, slots=True)
class FlowBucket:
    start: datetime
    end: datetime
    buy_volume: float
    sell_volume: float

    def __post_init__(self) -> None:
        _require_aware(self.start, "start")
        _require_aware(self.end, "end")
        if self.end <= self.start:
            raise ValueError("flow bucket end must be later than start")
        if self.buy_volume < 0 or self.sell_volume < 0:
            raise ValueError("flow volume cannot be negative")


@dataclass(frozen=True, slots=True)
class SeriesChange:
    start_value: float | None
    end_value: float | None
    absolute_change: float | None
    pct_change: float | None
    start_time: datetime | None
    end_time: datetime | None


@dataclass(frozen=True, slots=True)
class FlowAggregate:
    buy_volume: float
    sell_volume: float
    delta: float
    buy_sell_ratio: float | None
    covered_seconds: float
    requested_seconds: float
    buckets_used: int

    @property
    def coverage_ratio(self) -> float:
        if self.requested_seconds <= 0:
            return 0.0
        return min(1.0, self.covered_seconds / self.requested_seconds)


@dataclass(frozen=True, slots=True)
class GateAssessment:
    data_gate: str
    predictability_gate: str
    calibration_gate: str
    value_gate: str
    decision_quality: str
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ShadowReplayResult:
    symbol: str
    replay_version: str
    original_action: str
    evaluation: BarrierEvaluation
    open_interest: SeriesChange | None = None
    funding_rate: SeriesChange | None = None
    taker_flow: FlowAggregate | None = None
    top_trader_ratio: SeriesChange | None = None
    gates: GateAssessment | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_ready(asdict(self))


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value
