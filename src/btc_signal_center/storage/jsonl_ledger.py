from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from btc_signal_center.domain.models import ShadowReplayResult


class AppendOnlyJsonlLedger:
    """Durable append-only evidence ledger.

    A record is written as one JSON line, flushed, and fsynced before returning. Existing
    records are never rewritten by this class.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, result: ShadowReplayResult | dict[str, Any]) -> None:
        payload = result.to_dict() if isinstance(result, ShadowReplayResult) else result
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    records.append(json.loads(stripped))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSONL at line {line_number}") from exc
        return records
