from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from btc_signal_center.data.binance_public import BinancePublicClient
from btc_signal_center.data.raw_evidence import RawEvidenceManifestEntry, RawEvidenceStore


@dataclass(frozen=True, slots=True)
class BinanceCollectionSpec:
    symbol: str
    start_time: datetime
    end_time: datetime
    price_interval: str = "1m"
    derivative_period: str = "5m"

    def __post_init__(self) -> None:
        for name, value in (("start_time", self.start_time), ("end_time", self.end_time)):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        if self.symbol != "BTCUSDT":
            raise ValueError("shadow_v0.3 is intentionally restricted to BTCUSDT")

    @property
    def start_time_ms(self) -> int:
        return int(self.start_time.timestamp() * 1000)

    @property
    def end_time_ms(self) -> int:
        return int(self.end_time.timestamp() * 1000)


@dataclass(frozen=True, slots=True)
class BinanceCollectionReport:
    symbol: str
    start_time: str
    end_time: str
    entries: tuple[RawEvidenceManifestEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "entries": [asdict(entry) for entry in self.entries],
        }


def collect_shadow_window(
    spec: BinanceCollectionSpec,
    *,
    client: BinancePublicClient,
    store: RawEvidenceStore,
) -> BinanceCollectionReport:
    """Collect all public inputs needed to replay a short BTCUSDT shadow window."""

    common = {
        "symbol": spec.symbol,
        "start_time_ms": spec.start_time_ms,
        "end_time_ms": spec.end_time_ms,
    }
    responses = (
        client.mark_price_klines(interval=spec.price_interval, **common),
        client.trade_klines(interval=spec.price_interval, **common),
        client.open_interest_history(period=spec.derivative_period, **common),
        client.funding_rate_history(**common),
        client.top_trader_position_ratio(period=spec.derivative_period, **common),
    )
    entries = tuple(store.write(response) for response in responses)
    return BinanceCollectionReport(
        symbol=spec.symbol,
        start_time=spec.start_time.isoformat(),
        end_time=spec.end_time.isoformat(),
        entries=entries,
    )
