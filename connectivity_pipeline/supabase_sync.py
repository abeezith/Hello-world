from __future__ import annotations

import json
import os
import uuid
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import requests

from .providers import normalize_provider_name


@dataclass(frozen=True)
class SupabaseSettings:
    enabled: bool
    url: str
    api_key: str
    schema: str = "public"
    table_prefix: str = "connectivity"
    timeout_seconds: int = 30
    chunk_size: int = 500
    fail_on_error: bool = True
    sync_provider_rows: bool = True
    sync_village_summary: bool = True
    sync_run_metadata: bool = True


def load_supabase_settings(config: dict[str, Any]) -> SupabaseSettings:
    supabase_config = config.get("supabase", {})
    env_present = any(
        os.getenv(name)
        for name in [
            "SUPABASE_URL",
            "SUPABASE_PROJECT_URL",
            "SUPABASE_SERVICE_ROLE_KEY",
            "SUPABASE_ANON_KEY",
            "SUPABASE_KEY",
        ]
    )

    url = (
        os.getenv("SUPABASE_URL")
        or os.getenv("SUPABASE_PROJECT_URL")
        or str(supabase_config.get("url") or "")
    ).strip()
    api_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_KEY")
        or str(supabase_config.get("service_role_key") or supabase_config.get("anon_key") or "")
    ).strip()
    schema = str(os.getenv("SUPABASE_SCHEMA") or supabase_config.get("schema") or "public").strip() or "public"
    table_prefix = str(os.getenv("SUPABASE_TABLE_PREFIX") or supabase_config.get("table_prefix") or "connectivity").strip() or "connectivity"

    enabled_config = bool(supabase_config.get("enabled", False))
    enabled = bool(url and api_key and (enabled_config or env_present))

    return SupabaseSettings(
        enabled=enabled,
        url=url.rstrip("/"),
        api_key=api_key,
        schema=schema,
        table_prefix=table_prefix,
        timeout_seconds=int(supabase_config.get("timeout_seconds", 30)),
        chunk_size=max(int(supabase_config.get("chunk_size", 500)), 1),
        fail_on_error=bool(supabase_config.get("fail_on_error", True)),
        sync_provider_rows=bool(supabase_config.get("sync_provider_rows", True)),
        sync_village_summary=bool(supabase_config.get("sync_village_summary", True)),
        sync_run_metadata=bool(supabase_config.get("sync_run_metadata", True)),
    )


def sync_pipeline_outputs(
    config: dict[str, Any],
    provider_rows: pd.DataFrame,
    source_recency: dict[str, str] | None = None,
    villages_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    settings = load_supabase_settings(config)
    if not settings.enabled:
        return {"enabled": False, "synced": False, "tables": [], "run_id": None}

    run_id = f"{datetime.now(tz=UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:10]}"
    synced_tables: list[str] = []

    try:
        if settings.sync_provider_rows:
            provider_table = f"{settings.table_prefix}_provider_rows"
            provider_frame = provider_rows.copy()
            provider_frame["run_id"] = run_id
            provider_frame["synced_at_utc"] = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
            upsert_dataframe(
                settings=settings,
                table_name=provider_table,
                frame=provider_frame,
                on_conflict=["run_id", "village_id", "provider"],
            )
            synced_tables.append(provider_table)

        if settings.sync_village_summary:
            summary_table = f"{settings.table_prefix}_village_summary"
            summary_frame = build_village_summary_frame(provider_rows, run_id)
            summary_frame["synced_at_utc"] = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
            if source_recency:
                for key, value in source_recency.items():
                    summary_frame[key] = value
            upsert_dataframe(
                settings=settings,
                table_name=summary_table,
                frame=summary_frame,
                on_conflict=["run_id", "village_id"],
            )
            synced_tables.append(summary_table)

        if settings.sync_run_metadata:
            run_table = f"{settings.table_prefix}_runs"
            run_frame = build_run_metadata_frame(
                provider_rows=provider_rows,
                run_id=run_id,
                source_recency=source_recency or {},
            )
            upsert_dataframe(
                settings=settings,
                table_name=run_table,
                frame=run_frame,
                on_conflict=["run_id"],
            )
            synced_tables.append(run_table)
    except Exception:
        if settings.fail_on_error:
            raise
        return {"enabled": True, "synced": False, "tables": synced_tables, "run_id": run_id}

    return {"enabled": True, "synced": True, "tables": synced_tables, "run_id": run_id}


def build_village_summary_frame(provider_rows: pd.DataFrame, run_id: str) -> pd.DataFrame:
    metadata_columns = [
        column
        for column in [
            "opencellid_data_as_of",
            "opencellid_recency_basis",
            "ookla_data_as_of",
            "ookla_recency_basis",
            "data_as_of",
            "pipeline_generated_at_utc",
        ]
        if column in provider_rows.columns
    ]
    village_summary = (
        provider_rows.pivot_table(
            index=[
                "village_id",
                "state",
                "district",
                "block",
                "village",
                "lgd_code",
                "latitude",
                "longitude",
                "coordinate_source",
                *metadata_columns,
            ],
            columns="provider",
            values="coverage_score",
            aggfunc="first",
        )
        .reset_index()
    )

    renamed_columns: dict[str, str] = {}
    for column in village_summary.columns:
        if column in {
            "village_id",
            "state",
            "district",
            "block",
            "village",
            "lgd_code",
            "latitude",
            "longitude",
            "coordinate_source",
            *metadata_columns,
        }:
            continue
        renamed_columns[column] = f"{slugify(column)}_coverage_score"

    village_summary = village_summary.rename(columns=renamed_columns)
    village_summary.insert(0, "run_id", run_id)
    return village_summary


def build_run_metadata_frame(
    provider_rows: pd.DataFrame,
    run_id: str,
    source_recency: dict[str, str],
) -> pd.DataFrame:
    village_count = int(provider_rows["village_id"].nunique()) if "village_id" in provider_rows.columns else 0
    provider_count = int(provider_rows["provider"].nunique()) if "provider" in provider_rows.columns else 0
    summary = {
        "run_id": run_id,
        "generated_at_utc": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "village_count": village_count,
        "provider_count": provider_count,
        "provider_row_count": int(len(provider_rows)),
    }
    summary.update(source_recency)
    return pd.DataFrame([summary])


def upsert_dataframe(
    settings: SupabaseSettings,
    table_name: str,
    frame: pd.DataFrame,
    on_conflict: list[str] | tuple[str, ...],
) -> None:
    if frame.empty:
        return

    records = json.loads(frame.to_json(orient="records", date_format="iso"))
    url = f"{settings.url}/rest/v1/{table_name}"
    headers = {
        "apikey": settings.api_key,
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
        "Accept-Profile": settings.schema,
        "Content-Profile": settings.schema,
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    params = {"on_conflict": ",".join(on_conflict)}

    session = requests.Session()
    session.headers.update(headers)

    for start in range(0, len(records), settings.chunk_size):
        payload = records[start : start + settings.chunk_size]
        last_error: Exception | None = None
        for attempt in range(1, 6):
            response = session.post(
                url,
                params=params,
                json=payload,
                timeout=settings.timeout_seconds,
            )
            if response.ok:
                last_error = None
                break

            last_error = requests.HTTPError(
                f"{response.status_code} Client Error for url: {response.url} | body: {response.text[:500]}"
            )
            if response.status_code not in {404, 429, 500, 502, 503, 504} or attempt == 5:
                break

            time.sleep(min(2 ** (attempt - 1), 30))

        if last_error is not None:
            if "404 Client Error" in str(last_error):
                raise requests.HTTPError(
                    f"{last_error}\n"
                    "Supabase returned 404 for the REST endpoint. This usually means SUPABASE_URL is not the project API URL.\n"
                    "Use the Project URL from Supabase Dashboard -> Settings -> API / Integrations -> Data API, not the dashboard URL."
                )
            raise last_error


def slugify(value: str) -> str:
    text = normalize_provider_name(value)
    return "".join(char.lower() if char.isalnum() else "_" for char in text).strip("_")
