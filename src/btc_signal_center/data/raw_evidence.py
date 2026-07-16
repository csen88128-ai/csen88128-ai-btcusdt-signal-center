from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RawApiResponse:
    provider: str
    endpoint: str
    query_params: dict[str, str | int | float]
    request_url: str
    received_at: datetime
    status_code: int
    payload: bytes

    def __post_init__(self) -> None:
        if self.received_at.tzinfo is None or self.received_at.utcoffset() is None:
            raise ValueError("received_at must be timezone-aware")
        if self.status_code < 100:
            raise ValueError("status_code is invalid")

    @property
    def payload_sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()

    def json_payload(self) -> Any:
        return json.loads(self.payload.decode("utf-8"))


@dataclass(frozen=True, slots=True)
class RawEvidenceManifestEntry:
    provider: str
    endpoint: str
    query_params: dict[str, str | int | float]
    request_url: str
    received_at: str
    status_code: int
    payload_sha256: str
    payload_bytes: int
    relative_path: str


class RawEvidenceStore:
    """Persist raw public-market responses and an append-only manifest."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.payload_dir = self.root / "payloads"
        self.manifest_path = self.root / "manifest.jsonl"
        self.payload_dir.mkdir(parents=True, exist_ok=True)

    def write(self, response: RawApiResponse) -> RawEvidenceManifestEntry:
        timestamp = response.received_at.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        endpoint_slug = response.endpoint.strip("/").replace("/", "_") or "root"
        filename = f"{timestamp}_{response.provider.lower()}_{endpoint_slug}_{response.payload_sha256[:12]}.json"
        payload_path = self.payload_dir / filename

        self._write_once(payload_path, response.payload)
        entry = RawEvidenceManifestEntry(
            provider=response.provider,
            endpoint=response.endpoint,
            query_params=dict(response.query_params),
            request_url=response.request_url,
            received_at=response.received_at.isoformat(),
            status_code=response.status_code,
            payload_sha256=response.payload_sha256,
            payload_bytes=len(response.payload),
            relative_path=str(payload_path.relative_to(self.root)),
        )
        self._append_manifest(entry)
        return entry

    @staticmethod
    def _write_once(path: Path, payload: bytes) -> None:
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise ValueError(f"immutable raw payload collision: {path}") from None
            return
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

    def _append_manifest(self, entry: RawEvidenceManifestEntry) -> None:
        serialized = json.dumps(asdict(entry), ensure_ascii=False, separators=(",", ":"))
        with self.manifest_path.open("a", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
