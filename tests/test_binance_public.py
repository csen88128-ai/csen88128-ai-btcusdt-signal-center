from datetime import UTC, datetime
from urllib.error import URLError

from btc_signal_center.data.binance_public import BinancePublicClient


def test_client_builds_deterministic_public_request() -> None:
    calls: list[tuple[str, float]] = []

    def transport(url: str, timeout: float) -> tuple[int, bytes]:
        calls.append((url, timeout))
        return 200, b"[]"

    client = BinancePublicClient(
        transport=transport,
        clock=lambda: datetime(2026, 7, 16, 4, 0, tzinfo=UTC),
    )
    response = client.mark_price_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_time_ms=1000,
        end_time_ms=2000,
        limit=500,
    )

    assert calls == [
        (
            "https://fapi.binance.com/fapi/v1/markPriceKlines?"
            "endTime=2000&interval=1m&limit=500&startTime=1000&symbol=BTCUSDT",
            20.0,
        )
    ]
    assert response.status_code == 200
    assert response.json_payload() == []
    assert response.query_params["symbol"] == "BTCUSDT"


def test_client_retries_transient_transport_failure() -> None:
    attempts = 0
    sleeps: list[float] = []

    def transport(_url: str, _timeout: float) -> tuple[int, bytes]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise URLError("temporary")
        return 200, b"[]"

    client = BinancePublicClient(
        transport=transport,
        sleep=sleeps.append,
        max_attempts=2,
    )
    client.funding_rate_history(
        symbol="BTCUSDT",
        start_time_ms=1000,
        end_time_ms=2000,
    )

    assert attempts == 2
    assert sleeps == [1]
