from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def _iso_utc_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(float(timestamp), tz=UTC).isoformat().replace("+00:00", "Z")


def file_mtime_iso(path: Path) -> str:
    if not path.exists():
        return ""
    return _iso_utc_from_timestamp(path.stat().st_mtime)


def series_latest_iso(series: pd.Series | None) -> str:
    if series is None:
        return ""

    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if not numeric.empty:
        value = float(numeric.max())
        if value > 1_000_000_000_000:
            value /= 1000.0
        if value > 0:
            return _iso_utc_from_timestamp(value)

    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    parsed = parsed.dropna()
    if not parsed.empty:
        return parsed.max().isoformat().replace("+00:00", "Z")
    return ""


def data_recency_summary(*values: str) -> str:
    parsed = []
    for value in values:
        if not value:
            continue
        candidate = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.notna(candidate):
            parsed.append(candidate)
    if not parsed:
        return ""
    return min(parsed).isoformat().replace("+00:00", "Z")


def recency_payload(opencellid_value: str, ookla_value: str, generated_at: str | None = None) -> dict[str, str]:
    payload = {
        "opencellid_data_as_of": opencellid_value,
        "opencellid_recency_basis": "updated_column_or_mtime" if opencellid_value else "",
        "ookla_data_as_of": ookla_value,
        "ookla_recency_basis": "file_mtime" if ookla_value else "",
    }
    payload["data_as_of"] = data_recency_summary(opencellid_value, ookla_value)
    if generated_at:
        payload["pipeline_generated_at_utc"] = generated_at
    return payload

