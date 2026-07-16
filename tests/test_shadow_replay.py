from datetime import UTC, datetime, timedelta

from btc_signal_center.domain.models import (
    BarrierOutcome,
    BarrierSpec,
    Candle,
    FlowBucket,
    TimedValue,
)
from btc_signal_center.evaluation.shadow_replay import ReplayInputs, replay_shadow_event

START = datetime(2026, 7, 16, 3, 14, 8, tzinfo=UTC)


def test_observe_decision_passes_when_window_times_out_without_calibration() -> None:
    candles = tuple(
        Candle(
            open_time=datetime(2026, 7, 16, 3, minute, tzinfo=UTC),
            close_time=datetime(2026, 7, 16, 3, minute, tzinfo=UTC) + timedelta(minutes=1),
            open=100.0,
            high=100.8,
            low=99.3,
            close=100.1,
        )
        for minute in range(15, 44)
    )
    inputs = ReplayInputs(
        symbol="BTCUSDT",
        original_action="OBSERVE",
        spec=BarrierSpec(
            as_of=START,
            expires_at=START + timedelta(minutes=30),
            reference_price=100.0,
            upper=102.0,
            lower=98.0,
        ),
        candles=candles,
        open_interest=(
            TimedValue(START + timedelta(minutes=1), 1000),
            TimedValue(START + timedelta(minutes=26), 990),
        ),
        taker_flow=(
            FlowBucket(START + timedelta(minutes=1), START + timedelta(minutes=6), 20, 25),
            FlowBucket(START + timedelta(minutes=6), START + timedelta(minutes=11), 30, 20),
            FlowBucket(START + timedelta(minutes=11), START + timedelta(minutes=16), 15, 15),
        ),
    )

    result = replay_shadow_event(inputs)

    assert result.evaluation.outcome is BarrierOutcome.TIMEOUT
    assert result.open_interest is not None
    assert result.open_interest.pct_change == -0.01
    assert result.gates is not None
    assert result.gates.predictability_gate == "FAIL"
    assert result.gates.calibration_gate == "FAIL"
    assert result.gates.value_gate == "FAIL"
    assert result.gates.decision_quality == "PASS"
    assert result.to_dict()["evaluation"]["outcome"] == "TIMEOUT"
