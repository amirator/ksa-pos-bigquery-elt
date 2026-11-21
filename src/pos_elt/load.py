"""EL step: raw SAMA CSVs + Hijri calendar -> <warehouse>.pos_raw.*

* One raw table per source extract (A, B), replaced whole by a load job.
* SHA-256 change detection: an unchanged file is skipped (cheap weekly refresh).
* Every attempt, including failures, is appended to pos_raw.load_log; the loader
  carries on past a failed source and exits non-zero at the end.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

import pandas as pd

from .calendar import build_calendar
from .config import DATASETS, EXPECTED_COLUMNS, KNOWN_INDICATORS, RAW
from .warehouse import CALENDAR_SCHEMA, LOAD_LOG_SCHEMA, RAW_POS_SCHEMA, Warehouse


def file_sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_extract(path, source_code: str, sha: str, loaded_at: datetime) -> pd.DataFrame:
    """Read one KAPSARC CSV (UTF-8 with BOM) into the raw schema, validating its shape."""
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"sectors": str, "city": str})
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")
    unknown = set(df["number_value_change_transactions"].str.strip()) - KNOWN_INDICATORS
    if unknown:
        raise ValueError(f"{path.name}: unknown indicators {sorted(unknown)}")
    out = pd.DataFrame(
        {
            "source": source_code,
            "starting_date": pd.to_datetime(df["starting_date"], format="%Y-%m-%d").dt.date,
            "indicator": df["number_value_change_transactions"].str.strip(),
            "sector_raw": df["sectors"].str.strip(),
            "city_raw": df["city"].str.strip(),
            "value": pd.to_numeric(df["value"], errors="coerce").astype("float64"),
            "src_file_sha256": sha,
            "loaded_at": loaded_at,
        }
    )
    return out.sort_values(["starting_date", "indicator", "sector_raw", "city_raw"], kind="stable").reset_index(drop=True)


def _log_row(run_id, key, table, sha, rows, status, msg, wh, started) -> dict:
    return {
        "run_id": run_id, "source_key": key, "raw_table": table, "file_sha256": sha,
        "rows_loaded": int(rows), "status": status, "message": msg[:500], "warehouse": wh,
        "started_at": started, "finished_at": datetime.now(timezone.utc),
    }


def load_all(wh: Warehouse, force: bool = False) -> tuple[list[dict], bool]:
    """Load both extracts and the calendar. Returns (log rows, all_ok)."""
    run_id = uuid.uuid4().hex[:12]
    wh.ensure_dataset(wh.raw)
    log: list[dict] = []
    ok = True
    for key, meta in DATASETS.items():
        started = datetime.now(timezone.utc)
        path = RAW / f"{meta['dataset_id']}.csv"
        table = meta["raw_table"]
        sha = ""
        try:
            sha = file_sha256(path)
            if not force and sha == wh.last_successful_sha(key) and wh.table_exists(table):
                exp = wh.keep_alive(table)
                log.append(_log_row(run_id, key, table, sha, 0, "skipped_unchanged",
                                    "file hash unchanged since last load"
                                    + (f"; expiry extended to {exp}" if exp else ""), wh.kind, started))
                print(f"[load] {table:<16} unchanged (sha256 {sha[:10]}...), skipped"
                      + (f"; expiry extended to {exp}" if exp else ""))
                continue
            df = parse_extract(path, meta["source_code"], sha, started)
            n = wh.load_dataframe(table, df, RAW_POS_SCHEMA, mode="truncate")
            log.append(_log_row(run_id, key, table, sha, n, "loaded", "ok", wh.kind, started))
            print(f"[load] {table:<16} {n:>7,} rows -> {wh.raw}.{table}")
        except Exception as exc:  # keep going, record the failure, fail the run at the end
            ok = False
            log.append(_log_row(run_id, key, table, sha, 0, "failed", f"{type(exc).__name__}: {exc}",
                                wh.kind, started))
            print(f"[load] {table:<16} FAILED: {exc}")

    started = datetime.now(timezone.utc)
    cal = build_calendar()
    n = wh.load_dataframe("hijri_calendar", cal, CALENDAR_SCHEMA, mode="truncate")
    log.append(_log_row(run_id, "calendar", "hijri_calendar", "", n, "loaded", "ok", wh.kind, started))
    print(f"[load] {'hijri_calendar':<16} {n:>7,} rows -> {wh.raw}.hijri_calendar")

    wh.load_dataframe("load_log", pd.DataFrame(log), LOAD_LOG_SCHEMA, mode="append")
    wh.keep_alive("load_log")
    return log, ok
