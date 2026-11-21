"""BigQuery-dialect parity: the same dbt models, run on the BigQuery emulator, must return the
same 5 views as DuckDB. Runs in CI after the emulator job exports outputs/bq_emulator/."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
EMU = ROOT / "outputs" / "bq_emulator"
VIEWS = {"vw_weekly_kpis": ["week_start"], "vw_yearly_avg_ticket": ["year"],
         "vw_city_share": ["city_name", "year"], "vw_ramadan_eid_lift": ["year"],
         "vw_latest_vs_prior_year": ["cur_from"]}


@pytest.mark.parametrize("view,keys", VIEWS.items())
def test_emulator_matches_duckdb(view, keys):
    if not (EMU / f"{view}.csv").exists():
        pytest.skip("BigQuery emulator outputs not present (CI job `bigquery-emulator` creates them)")
    a = pd.read_csv(ROOT / "outputs" / f"{view}.csv").sort_values(keys).reset_index(drop=True)
    b = pd.read_csv(EMU / f"{view}.csv").sort_values(keys).reset_index(drop=True)
    assert list(a.columns) == list(b.columns) and a.shape == b.shape
    for col in a.columns:
        if pd.api.types.is_numeric_dtype(a[col]) and a[col].dtype != bool:
            assert np.allclose(a[col].astype(float), b[col].astype(float), rtol=1e-6, equal_nan=True), col
        else:
            assert (a[col].astype(str).str.lower() == b[col].astype(str).str.lower()).all(), col
