"""Unit tests: settings, calendar, CSV parsing, loader change-detection and failure logging."""
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from pos_elt import load as load_mod
from pos_elt.calendar import build_calendar
from pos_elt.config import Settings, settings_from_env
from pos_elt.load import parse_extract
from pos_elt.warehouse import DuckDBWarehouse


# ---- settings / adapter switch ---------------------------------------------------
def test_default_is_local_duckdb():
    s = settings_from_env(env={})
    assert s.kind == "duckdb" and s.dbt_target == "duckdb" and s.bq_api_endpoint is None


def test_bigquery_requires_project():
    with pytest.raises(ValueError, match="BQ_PROJECT"):
        settings_from_env(env={"WAREHOUSE": "bigquery"})
    s = settings_from_env(env={"WAREHOUSE": "bigquery", "BQ_PROJECT": "p1", "BQ_LOCATION": "me-central2"})
    assert (s.dbt_target, s.bq_project, s.bq_location, s.bq_api_endpoint) == ("bigquery", "p1", "me-central2", None)


def test_emulator_defaults():
    s = settings_from_env(env={"WAREHOUSE": "bq-emulator"})
    assert s.dbt_target == "bq_emulator" and s.bq_api_endpoint == "http://localhost:9050"


def test_unknown_warehouse_rejected():
    with pytest.raises(ValueError):
        settings_from_env(env={"WAREHOUSE": "snowflake"})


# ---- Hijri calendar ------------------------------------------------------------------
@pytest.fixture(scope="module")
def cal():
    return build_calendar().set_index("week_start")


def test_calendar_weeks_are_sundays(cal):
    assert all(d.weekday() == 6 for d in cal.index)
    assert cal.index.is_unique and cal.index.is_monotonic_increasing


def test_ramadan_and_eid_2024(cal):
    # Ramadan 1445 began Mon 11 Mar 2024; Eid al-Fitr was Wed 10 Apr 2024 (Umm al-Qura)
    assert cal.loc[date(2024, 3, 10), "is_ramadan_week"]
    assert not cal.loc[date(2024, 3, 3), "is_ramadan_week"]
    assert cal.loc[date(2024, 4, 7), "is_eid_fitr_week"]
    assert cal.is_eid_fitr_week.groupby(cal.year).sum().loc[2021:2027].eq(1).all()


# ---- CSV parsing ---------------------------------------------------------------------
HEADER = "\ufeffstarting_date,number_value_change_transactions,sectors,city,value\n"


def _csv(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(HEADER + body, encoding="utf-8")
    return p


def test_parse_handles_bom_and_types(tmp_path):
    p = _csv(tmp_path, "a.csv", "2024-01-07,Value of Transactions (In Thousand SAR),Total,Total,12345.5\n")
    df = parse_extract(p, "A", "abc", datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert list(df.columns)[:6] == ["source", "starting_date", "indicator", "sector_raw", "city_raw", "value"]
    assert df.loc[0, "starting_date"] == date(2024, 1, 7) and df.loc[0, "value"] == 12345.5


def test_parse_rejects_unknown_indicator(tmp_path):
    p = _csv(tmp_path, "a.csv", "2024-01-07,Something New,Total,Total,1\n")
    with pytest.raises(ValueError, match="unknown indicators"):
        parse_extract(p, "A", "abc", datetime.now(timezone.utc))


# ---- loader: hash skip, reload on change, failures logged ------------------------
@pytest.fixture()
def tiny_env(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    datasets = {
        "pos_a": {"dataset_id": "a", "raw_table": "sama_pos_a", "source_code": "A"},
        "pos_b": {"dataset_id": "b", "raw_table": "sama_pos_b", "source_code": "B"},
    }
    monkeypatch.setattr(load_mod, "RAW", raw)
    monkeypatch.setattr(load_mod, "DATASETS", datasets)
    _csv(raw, "a.csv", "2024-01-07,Value of Transactions (In Thousand SAR),Total,Total,1\n")
    _csv(raw, "b.csv", "2025-07-06,Value of Transactions (In Thousand SAR),20.Total,Total,2\n")
    s = Settings("duckdb", "pos_raw", "pos_reporting", tmp_path / "t.duckdb", None, "US", None)
    wh = DuckDBWarehouse(s)
    yield raw, wh
    wh.close()


def test_loader_skips_unchanged_and_reloads_changed(tiny_env):
    raw, wh = tiny_env
    log1, ok1 = load_mod.load_all(wh)
    assert ok1 and [r["status"] for r in log1[:2]] == ["loaded", "loaded"]
    log2, _ = load_mod.load_all(wh)
    assert [r["status"] for r in log2[:2]] == ["skipped_unchanged", "skipped_unchanged"]
    _csv(raw, "b.csv", "2025-07-06,Value of Transactions (In Thousand SAR),20.Total,Total,3\n")
    log3, _ = load_mod.load_all(wh)
    assert [r["status"] for r in log3[:2]] == ["skipped_unchanged", "loaded"]
    assert wh.query_df('select value from "pos_raw"."sama_pos_b"').value.tolist() == [3.0]
    n = wh.query_df('select count(*) n from "pos_raw"."load_log"').n.iloc[0]
    assert n == 9  # 3 runs x (A, B, calendar)


def test_loader_logs_failure_and_continues(tiny_env):
    raw, wh = tiny_env
    (raw / "a.csv").write_text("not,the,right,columns\n1,2,3,4\n")
    log, ok = load_mod.load_all(wh)
    assert not ok
    statuses = {r["source_key"]: r["status"] for r in log}
    assert statuses == {"pos_a": "failed", "pos_b": "loaded", "calendar": "loaded"}
    logged = wh.query_df('select status from "pos_raw"."load_log" where source_key = \'pos_a\'')
    assert logged.status.tolist() == ["failed"]
