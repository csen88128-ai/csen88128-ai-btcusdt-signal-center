from datetime import UTC, datetime, timedelta

import pytest

from btc_signal_center.data.binance_collector import (
    BinanceCollectionSpec,
    collect_shadow_window,
)
from btc_signal_center.data.raw_evidence import RawApiResponse, RawEvidenceStore


class FakeClient:
    received_at = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)

    def _response(self, endpoint: str) -> RawApiResponse:
        return RawApiResponse(
            provider="Binance",
            endpoint=endpoint,
            query_params={"symbol": "BTCUSDT"},
            request_url=f"https://example.test{endpoint}?symbol=BTCUSDT",
            received_at=self.received_at,
            status_code=200,
            payload=b"[]",
        )

    def mark_price_klines(self, **_kwargs) -> RawApiResponse:
        return self._response("/fapi/v1/markPriceKlines")

    def trade_klines(self, **_kwargs) -> RawApiResponse:
        return self._response("/fapi/v1/klines")

    def open_interest_history(self, **_kwargs) -> RawApiResponse:
        return self._response("/futures/data/openInterestHist")

    def funding_rate_history(self, **_kwargs) -> RawApiResponse:
        return self._response("/fapi/v1/fundingRate")

    def top_trader_position_ratio(self, **_kwargs) -> RawApiResponse:
        return self._response("/futures/data/topLongShortPositionRatio")


def test_collector_persists_all_required_public_sources(tmp_path) -> None:
    start = datetime(2026, 7, 16, 3, 14, 8, tzinfo=UTC)
    spec = BinanceCollectionSpec(
        symbol="BTCUSDT",
        start_time=start,
        end_time=start + timedelta(hours=8),
    )

    report = collect_shadow_window(
        spec,
        client=FakeClient(),  # type: ignore[arg-type]
        store=RawEvidenceStore(tmp_path),
    )

    assert report.symbol == "BTCUSDT"
    assert len(report.entries) == 5
    assert {entry.endpoint for entry in report.entries} == {
        "/fapi/v1/markPriceKlines",
        "/fapi/v1/klines",
        "/futures/data/openInterestHist",
        "/fapi/v1/fundingRate",
        "/futures/data/topLongShortPositionRatio",
    }
    assert len((tmp_path / "manifest.jsonl").read_text().splitlines()) == 5


def test_collection_spec_rejects_scope_expansion() -> None:
    start = datetime(2026, 7, 16, tzinfo=UTC)
    with pytest.raises(ValueError, match="restricted to BTCUSDT"):
        BinanceCollectionSpec(
            symbol="ETHUSDT",
            start_time=start,
            end_time=start + timedelta(hours=1),
        )
