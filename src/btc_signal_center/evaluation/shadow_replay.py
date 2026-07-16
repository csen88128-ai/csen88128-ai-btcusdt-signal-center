from __future__ import annotations

from dataclasses import dataclass

from btc_signal_center.domain.models import (
    BarrierOutcome,
    BarrierSpec,
    Candle,
    FlowBucket,
    GateAssessment,
    ShadowReplayResult,
    TimedValue,
)
from btc_signal_center.features.event_window import aggregate_full_flow_buckets, endpoint_change
from btc_signal_center.labels.triple_barrier import PathLabelPolicy, evaluate_triple_barrier


@dataclass(frozen=True, slots=True)
class ReplayInputs:
    symbol: str
    original_action: str
    spec: BarrierSpec
    candles: tuple[Candle, ...]
    open_interest: tuple[TimedValue, ...] = ()
    funding_rate: tuple[TimedValue, ...] = ()
    taker_flow: tuple[FlowBucket, ...] = ()
    top_trader_ratio: tuple[TimedValue, ...] = ()
    calibrated_probability_available: bool = False
    net_ev_lower_bound: float | None = None


def replay_shadow_event(
    inputs: ReplayInputs,
    *,
    path_policy: PathLabelPolicy | None = None,
    metadata: dict[str, object] | None = None,
) -> ShadowReplayResult:
    evaluation = evaluate_triple_barrier(inputs.candles, inputs.spec, path_policy=path_policy)
    start = inputs.spec.as_of
    end = inputs.spec.expires_at

    oi_change = endpoint_change(inputs.open_interest, start=start, end=end)
    funding_change = endpoint_change(inputs.funding_rate, start=start, end=end)
    ratio_change = endpoint_change(inputs.top_trader_ratio, start=start, end=end)
    flow = aggregate_full_flow_buckets(inputs.taker_flow, start=start, end=end)

    gates = _assess_gates(
        original_action=inputs.original_action,
        outcome=evaluation.outcome,
        price_coverage=evaluation.metrics.price_coverage_ratio,
        derivative_coverage=flow.coverage_ratio,
        calibrated_probability_available=inputs.calibrated_probability_available,
        net_ev_lower_bound=inputs.net_ev_lower_bound,
    )

    return ShadowReplayResult(
        symbol=inputs.symbol,
        replay_version="shadow_v0.2",
        original_action=inputs.original_action,
        evaluation=evaluation,
        open_interest=oi_change,
        funding_rate=funding_change,
        taker_flow=flow,
        top_trader_ratio=ratio_change,
        gates=gates,
        metadata=dict(metadata or {}),
    )


def _assess_gates(
    *,
    original_action: str,
    outcome: BarrierOutcome,
    price_coverage: float,
    derivative_coverage: float,
    calibrated_probability_available: bool,
    net_ev_lower_bound: float | None,
) -> GateAssessment:
    reasons: list[str] = []

    data_gate = "PASS"
    if price_coverage < 0.90:
        data_gate = "FAIL"
        reasons.append("PRICE_COVERAGE_BELOW_90_PERCENT")
    elif derivative_coverage < 0.50:
        data_gate = "PARTIAL"
        reasons.append("DERIVATIVE_WINDOW_COVERAGE_BELOW_50_PERCENT")

    calibration_gate = "PASS" if calibrated_probability_available else "FAIL"
    if not calibrated_probability_available:
        reasons.append("CALIBRATED_PROBABILITY_UNAVAILABLE")

    value_gate = "PASS" if net_ev_lower_bound is not None and net_ev_lower_bound > 0 else "FAIL"
    if net_ev_lower_bound is None:
        reasons.append("NET_EV_LOWER_BOUND_UNAVAILABLE")
    elif net_ev_lower_bound <= 0:
        reasons.append("NET_EV_LOWER_BOUND_NON_POSITIVE")

    predictability_gate = "PASS"
    if outcome in {BarrierOutcome.TIMEOUT, BarrierOutcome.AMBIGUOUS}:
        predictability_gate = "FAIL"
        reasons.append(f"BARRIER_OUTCOME_{outcome.value}")

    action = original_action.upper()
    if action in {"OBSERVE", "REJECT"}:
        decision_quality = "PASS" if predictability_gate == "FAIL" else "INCONCLUSIVE"
    else:
        decision_quality = "FAIL" if outcome is BarrierOutcome.AMBIGUOUS else "INCONCLUSIVE"

    return GateAssessment(
        data_gate=data_gate,
        predictability_gate=predictability_gate,
        calibration_gate=calibration_gate,
        value_gate=value_gate,
        decision_quality=decision_quality,
        reasons=tuple(reasons),
    )
