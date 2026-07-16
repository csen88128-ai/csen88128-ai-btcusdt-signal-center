from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from btc_signal_center.data.binance_collector import (
    BinanceCollectionSpec,
    collect_shadow_window,
)
from btc_signal_center.data.binance_public import BinancePublicClient
from btc_signal_center.data.raw_evidence import RawEvidenceStore
from btc_signal_center.domain.models import BarrierSpec, Candle, FlowBucket, TimedValue
from btc_signal_center.evaluation.shadow_replay import ReplayInputs, replay_shadow_event
from btc_signal_center.storage.jsonl_ledger import AppendOnlyJsonlLedger


def main() -> None:
    parser = argparse.ArgumentParser(prog="btc-shadow-replay")
    subparsers = parser.add_subparsers(dest="command", required=True)

    replay_parser = subparsers.add_parser("replay", help="replay a frozen shadow event")
    replay_parser.add_argument("--input", required=True, type=Path)
    replay_parser.add_argument("--ledger", type=Path)

    collect_parser = subparsers.add_parser(
        "collect-binance",
        help="collect immutable Binance public evidence for a frozen event window",
    )
    collect_parser.add_argument("--symbol", default="BTCUSDT")
    collect_parser.add_argument("--start", required=True)
    collect_parser.add_argument("--end", required=True)
    collect_parser.add_argument("--output", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "replay":
        _run_replay(args)
    elif args.command == "collect-binance":
        _run_collection(args)


def _run_replay(args: argparse.Namespace) -> None:
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = replay_shadow_event(_parse_inputs(payload), metadata=payload.get("metadata"))
    output = result.to_dict()
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if args.ledger:
        AppendOnlyJsonlLedger(args.ledger).append(output)


def _run_collection(args: argparse.Namespace) -> None:
    spec = BinanceCollectionSpec(
        symbol=args.symbol,
        start_time=_dt(args.start),
        end_time=_dt(args.end),
    )
    report = collect_shadow_window(
        spec,
        client=BinancePublicClient(),
        store=RawEvidenceStore(args.output),
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


def _parse_inputs(payload: dict[str, Any]) -> ReplayInputs:
    spec_payload = payload["barrier_spec"]
    spec = BarrierSpec(
        as_of=_dt(spec_payload["as_of"]),
        expires_at=_dt(spec_payload["expires_at"]),
        reference_price=float(spec_payload["reference_price"]),
        upper=float(spec_payload["upper"]),
        lower=float(spec_payload["lower"]),
    )
    candles = tuple(
        Candle(
            open_time=_dt(item["open_time"]),
            close_time=_dt(item["close_time"]),
            open=float(item["open"]),
            high=float(item["high"]),
            low=float(item["low"]),
            close=float(item["close"]),
        )
        for item in payload["candles"]
    )
    return ReplayInputs(
        symbol=payload.get("symbol", "BTCUSDT"),
        original_action=payload.get("original_action", "OBSERVE"),
        spec=spec,
        candles=candles,
        open_interest=_timed_values(payload.get("open_interest", [])),
        funding_rate=_timed_values(payload.get("funding_rate", [])),
        taker_flow=tuple(
            FlowBucket(
                start=_dt(item["start"]),
                end=_dt(item["end"]),
                buy_volume=float(item["buy_volume"]),
                sell_volume=float(item["sell_volume"]),
            )
            for item in payload.get("taker_flow", [])
        ),
        top_trader_ratio=_timed_values(payload.get("top_trader_ratio", [])),
        calibrated_probability_available=bool(
            payload.get("calibrated_probability_available", False)
        ),
        net_ev_lower_bound=(
            None
            if payload.get("net_ev_lower_bound") is None
            else float(payload["net_ev_lower_bound"])
        ),
    )


def _timed_values(items: list[dict[str, Any]]) -> tuple[TimedValue, ...]:
    return tuple(
        TimedValue(timestamp=_dt(item["timestamp"]), value=float(item["value"]))
        for item in items
    )


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp must be timezone-aware: {value}")
    return parsed


if __name__ == "__main__":
    main()
