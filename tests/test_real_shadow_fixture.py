import json
from pathlib import Path

EVIDENCE_PATH = Path(
    "evidence/shadow/2026-07-16T031408+0800_BTCUSDT_summary.json"
)


def test_first_shadow_evidence_is_price_verified_and_non_actionable() -> None:
    record = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    assert record["symbol"] == "BTCUSDT"
    assert record["status"] == "FINALIZED_PRICE_ONLY"
    assert record["original_action"] == "OBSERVE"
    assert record["original_weights_are_calibrated"] is False
    assert record["derivatives"]["status"] == "PENDING_VERIFICATION"
    assert record["assessment"]["decision_quality"] == "PASS"
    assert record["assessment"]["calibration_status"] == "NOT_READY"
    assert record["assessment"]["value_status"] == "NOT_READY"


def test_all_frozen_horizons_timeout_without_barrier_touch() -> None:
    record = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    horizons = {item["horizon"]: item for item in record["frozen_horizons"]}

    assert set(horizons) == {"30m", "2h", "8h"}
    for item in horizons.values():
        result = item["result"]
        assert result["primary_label"] == "TIMEOUT"
        assert result["barrier_touch"] == {
            "up": False,
            "down": False,
            "ambiguous_same_bar": False,
        }
        assert result["high_price"] < item["upper_barrier"]
        assert result["low_price"] > item["lower_barrier"]


def test_horizon_paths_capture_materially_different_timeout_behaviour() -> None:
    record = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    horizons = {item["horizon"]: item["result"] for item in record["frozen_horizons"]}

    assert horizons["30m"]["path_label"] == "TIMEOUT_UP_BIAS"
    assert horizons["2h"]["path_label"] == "TIMEOUT_MEAN_REVERT"
    assert horizons["8h"]["path_label"] == "TIMEOUT_DOWN_BIAS"
    assert horizons["8h"]["short_mfe_pct"] > 0.008
    assert horizons["8h"]["cutoff_price"] == 64684.75162319
