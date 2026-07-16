from datetime import UTC, datetime

from btc_signal_center.data.binance_adapters import (
    parse_funding_rate_history,
    parse_mark_price_klines,
    parse_open_interest_history,
    parse_top_trader_position_ratio,
    parse_trade_kline_flow,
)


def test_parse_mark_price_and_exact_trade_flow() -> None:
    mark_rows = [
        [1000, "100", "103", "98", "101", "0", 60999, "0", 60, "0", "0", "0"]
    ]
    trade_rows = [
        [1000, "100", "103", "98", "101", "100", 60999, "0", 60, "60", "0", "0"]
    ]

    candle = parse_mark_price_klines(mark_rows)[0]
    flow = parse_trade_kline_flow(trade_rows)[0]

    assert candle.open_time == datetime.fromtimestamp(1, tz=UTC)
    assert candle.close_time == datetime.fromtimestamp(60.999, tz=UTC)
    assert candle.high == 103
    assert candle.low == 98
    assert flow.buy_volume == 60
    assert flow.sell_volume == 40
    assert flow.start == candle.open_time
    assert flow.end == candle.close_time


def test_parse_derivative_series() -> None:
    oi = parse_open_interest_history(
        [{"timestamp": 1000, "sumOpenInterest": "123.4"}]
    )[0]
    funding = parse_funding_rate_history(
        [{"fundingTime": 2000, "fundingRate": "0.0001"}]
    )[0]
    ratio = parse_top_trader_position_ratio(
        [{"timestamp": 3000, "longShortRatio": "1.25"}]
    )[0]

    assert oi.value == 123.4
    assert funding.value == 0.0001
    assert ratio.value == 1.25
    assert oi.timestamp == datetime.fromtimestamp(1, tz=UTC)
