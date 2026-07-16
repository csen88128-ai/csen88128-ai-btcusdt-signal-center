from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from btc_signal_center.data.raw_evidence import RawApiResponse

Transport = Callable[[str, float], tuple[int, bytes]]


class BinancePublicClient:
    """Read-only Binance USDⓈ-M public market-data client.

    The client deliberately exposes no account, order or position endpoints. A transport can
    be injected for deterministic tests.
    """

    def __init__(
        self,
        *,
        base_url: str = "https://fapi.binance.com",
        timeout_seconds: float = 20.0,
        max_attempts: int = 3,
        transport: Transport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.transport = transport or _default_transport
        self.sleep = sleep
        self.clock = clock or (lambda: datetime.now(UTC))

    def mark_price_klines(
        self,
        *,
        symbol: str,
        interval: str,
        start_time_ms: int,
        end_time_ms: int,
        limit: int = 1500,
    ) -> RawApiResponse:
        return self._get(
            "/fapi/v1/markPriceKlines",
            {
                "symbol": symbol,
                "interval": interval,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
                "limit": limit,
            },
        )

    def trade_klines(
        self,
        *,
        symbol: str,
        interval: str,
        start_time_ms: int,
        end_time_ms: int,
        limit: int = 1500,
    ) -> RawApiResponse:
        return self._get(
            "/fapi/v1/klines",
            {
                "symbol": symbol,
                "interval": interval,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
                "limit": limit,
            },
        )

    def open_interest_history(
        self,
        *,
        symbol: str,
        period: str,
        start_time_ms: int,
        end_time_ms: int,
        limit: int = 500,
    ) -> RawApiResponse:
        return self._get(
            "/futures/data/openInterestHist",
            {
                "symbol": symbol,
                "period": period,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
                "limit": limit,
            },
        )

    def funding_rate_history(
        self,
        *,
        symbol: str,
        start_time_ms: int,
        end_time_ms: int,
        limit: int = 1000,
    ) -> RawApiResponse:
        return self._get(
            "/fapi/v1/fundingRate",
            {
                "symbol": symbol,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
                "limit": limit,
            },
        )

    def top_trader_position_ratio(
        self,
        *,
        symbol: str,
        period: str,
        start_time_ms: int,
        end_time_ms: int,
        limit: int = 500,
    ) -> RawApiResponse:
        return self._get(
            "/futures/data/topLongShortPositionRatio",
            {
                "symbol": symbol,
                "period": period,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
                "limit": limit,
            },
        )

    def _get(
        self,
        endpoint: str,
        params: Mapping[str, str | int | float],
    ) -> RawApiResponse:
        normalized = {key: value for key, value in params.items() if value is not None}
        query = urlencode(sorted(normalized.items()))
        request_url = f"{self.base_url}{endpoint}?{query}"
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                status_code, payload = self.transport(request_url, self.timeout_seconds)
                if not 200 <= status_code < 300:
                    raise RuntimeError(f"Binance returned HTTP {status_code}")
                return RawApiResponse(
                    provider="Binance",
                    endpoint=endpoint,
                    query_params=dict(normalized),
                    request_url=request_url,
                    received_at=self.clock(),
                    status_code=status_code,
                    payload=payload,
                )
            except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
                last_error = exc
                if attempt < self.max_attempts:
                    self.sleep(min(2 ** (attempt - 1), 8))

        raise RuntimeError(f"Binance public request failed: {request_url}") from last_error


def _default_transport(url: str, timeout_seconds: float) -> tuple[int, bytes]:
    request = Request(url, headers={"User-Agent": "btc-signal-center/0.3"})
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        return int(response.status), response.read()
