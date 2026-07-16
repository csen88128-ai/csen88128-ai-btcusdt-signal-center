import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime

from btc_signal_center.data.raw_evidence import RawApiResponse, RawEvidenceStore


def test_raw_store_preserves_payload_and_appends_manifest(tmp_path) -> None:
    payload = b'[{"value":1}]'
    response = RawApiResponse(
        provider="Binance",
        endpoint="/fapi/v1/markPriceKlines",
        query_params={"symbol": "BTCUSDT", "interval": "1m"},
        request_url=(
            "https://fapi.binance.com/fapi/v1/markPriceKlines?"
            "interval=1m&symbol=BTCUSDT"
        ),
        received_at=datetime(2026, 7, 16, 4, 0, tzinfo=UTC),
        status_code=200,
        payload=payload,
    )

    store = RawEvidenceStore(tmp_path)
    entry = store.write(response)

    assert entry.payload_sha256 == hashlib.sha256(payload).hexdigest()
    assert (tmp_path / entry.relative_path).read_bytes() == payload
    manifest = [json.loads(line) for line in store.manifest_path.read_text().splitlines()]
    assert manifest == [asdict(entry)]
    assert manifest[0]["query_params"]["symbol"] == "BTCUSDT"
