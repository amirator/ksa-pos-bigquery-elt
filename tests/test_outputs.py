"""Output tests: KPIs reconcile with the published ksa-pos-spending-dashboard numbers,
README matches kpis.json (drift test), and the warehouse matches the exported CSVs."""
import json
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
KPIS = json.loads((ROOT / "outputs" / "kpis.json").read_text())
README = (ROOT / "README.md").read_text()


def test_coverage():
    c = KPIS["coverage"]
    assert (c["first_week"], c["weeks"], c["weeks_from_release_b"]) == ("2020-05-10", 307, 37)
    assert c["full_years"] == [2021, 2022, 2023, 2024, 2025]


def test_reconciles_with_original_dashboard_repo():
    """Same SAMA data, rebuilt with dbt: must reproduce github.com/amirator/ksa-pos-spending-dashboard."""
    y = KPIS["yearly"]
    assert (y["avg_weekly_value_bn_sar_first"], y["avg_weekly_value_bn_sar_last"]) == (9.08, 13.57)
    assert (y["value_growth_pct"], y["txn_growth_pct"]) == (49.3, 123.1)
    assert (y["avg_ticket_sar_first"], y["avg_ticket_sar_last"], y["avg_ticket_change_pct"]) == (91.4, 61.2, -33.1)
    assert KPIS["city_share"] == {"riyadh_first": 31.0, "riyadh_last": 34.6, "jeddah_first": 16.1, "jeddah_last": 14.0}
    r = KPIS["ramadan_eid"]
    assert (r["peak_index_min"], r["peak_index_median"], r["peak_index_max"]) == (104.0, 116.0, 145.0)
    assert KPIS["latest_ytd"]["value_yoy_pct"] == 3.4


def _fmt(x):
    return f"{x:g}" if float(x) != int(x) else f"{int(x)}"


@pytest.mark.parametrize("path", [
    ("yearly", "avg_weekly_value_bn_sar_first"), ("yearly", "avg_weekly_value_bn_sar_last"),
    ("yearly", "value_growth_pct"), ("yearly", "txn_growth_pct"),
    ("yearly", "avg_ticket_sar_first"), ("yearly", "avg_ticket_sar_last"),
    ("city_share", "riyadh_first"), ("city_share", "riyadh_last"),
    ("city_share", "jeddah_first"), ("city_share", "jeddah_last"),
    ("latest_ytd", "value_yoy_pct"), ("coverage", "weeks"),
])
def test_readme_numbers_match_kpis(path):
    v = KPIS[path[0]][path[1]]
    s = f"{v:.1f}" if isinstance(v, float) and path[1] not in ("avg_weekly_value_bn_sar_first", "avg_weekly_value_bn_sar_last") else (f"{v:.2f}" if isinstance(v, float) else str(v))
    assert s in README, f"README is out of date: {path} = {s} not found"


def test_readme_is_honest_about_cloud_status():
    assert "BigQuery-ready" in README
    assert not re.search(r"(?i)\b(is|now) (live|deployed) (on|to) BigQuery\b", README)


@pytest.mark.parametrize("view", ["vw_weekly_kpis", "vw_yearly_avg_ticket", "vw_city_share",
                                  "vw_ramadan_eid_lift", "vw_latest_vs_prior_year"])
def test_exported_csvs_match_local_warehouse(view):
    db = ROOT / "warehouse" / "ksa_pos.duckdb"
    if not db.exists():
        pytest.skip("run `python -m pos_elt.pipeline` first")
    import duckdb

    con = duckdb.connect(str(db), read_only=True)
    live = con.execute(f'select count(*) from "pos_reporting"."{view}"').fetchone()[0]
    con.close()
    assert live == len(pd.read_csv(ROOT / "outputs" / f"{view}.csv"))
