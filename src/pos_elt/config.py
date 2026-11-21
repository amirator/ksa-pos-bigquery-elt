"""Paths, dataset identifiers and warehouse settings.

Dataset identifiers and the KAPSARC export URL are reused from
github.com/amirator/ksa-pos-spending-dashboard (src/pos_dashboard/config.py).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
WAREHOUSE_DIR = ROOT / "warehouse"
OUTPUTS = ROOT / "outputs"
DOCS_IMG = ROOT / "docs" / "img"
DBT_DIR = ROOT / "dbt"

KAPSARC_EXPORT = (
    "https://datasource.kapsarc.org/api/explore/v2.1/catalog/datasets/"
    "{dataset_id}/exports/csv?delimiter=%2C"
)
KAPSARC_PAGE = "https://datasource.kapsarc.org/explore/dataset/{dataset_id}/"

DATASETS = {
    # A: weekly, May 2020 - Jul 2025, 17 sectors (national) + 11 cities
    "pos_a": {
        "dataset_id": "point-of-sale-transactions-by-sector-and-city",
        "raw_table": "sama_pos_a",
        "source_code": "A",
        "title": "Point of Sale Transactions by Sector and City",
        "publisher": "Saudi Central Bank (SAMA)",
        "license": "Public Domain (as labelled on the KAPSARC Data Portal); source copyright SAMA",
    },
    # B: weekly, Jun 2025 onwards, 32 sub-sectors + 61 cities (new taxonomy)
    "pos_b": {
        "dataset_id": "detailed-point-of-sale-transactions-by-sector-and-city",
        "raw_table": "sama_pos_b",
        "source_code": "B",
        "title": "Detailed Point of Sale Transactions by Sector and City",
        "publisher": "Saudi Central Bank (SAMA)",
        "license": "Public Domain (as labelled on the KAPSARC Data Portal); source copyright SAMA",
    },
}

EXPECTED_COLUMNS = ["starting_date", "number_value_change_transactions", "sectors", "city", "value"]
KNOWN_INDICATORS = {
    "Number of Transactions (In Thousand)",
    "Value of Transactions (In Thousand SAR)",
    "Number of Transactions Change %",
    "Value of Transactions Change %",
}

# dbt target name for each warehouse kind
WAREHOUSE_KINDS = {"duckdb": "duckdb", "bigquery": "bigquery", "bq-emulator": "bq_emulator"}

REPORTING_VIEWS = [
    "vw_weekly_kpis",
    "vw_yearly_avg_ticket",
    "vw_city_share",
    "vw_ramadan_eid_lift",
    "vw_latest_vs_prior_year",
]


@dataclass(frozen=True)
class Settings:
    kind: str
    raw_dataset: str
    reporting_dataset: str
    duckdb_path: Path
    bq_project: str | None
    bq_location: str
    bq_api_endpoint: str | None

    @property
    def dbt_target(self) -> str:
        return WAREHOUSE_KINDS[self.kind]


def settings_from_env(kind: str | None = None, env: dict | None = None) -> Settings:
    """Resolve warehouse settings. WAREHOUSE=duckdb (default) | bigquery | bq-emulator."""
    env = dict(os.environ if env is None else env)
    kind = (kind or env.get("WAREHOUSE") or "duckdb").strip().lower()
    if kind not in WAREHOUSE_KINDS:
        raise ValueError(f"WAREHOUSE must be one of {sorted(WAREHOUSE_KINDS)}, got {kind!r}")
    endpoint = None
    project = env.get("BQ_PROJECT") or None
    if kind == "bq-emulator":
        endpoint = env.get("BQ_API_ENDPOINT", "http://localhost:9050")
        project = project or "ksa-pos-local"
    if kind == "bigquery" and not project:
        raise ValueError("WAREHOUSE=bigquery needs BQ_PROJECT (your Google Cloud project id)")
    return Settings(
        kind=kind,
        raw_dataset=env.get("RAW_DATASET", "pos_raw"),
        reporting_dataset=env.get("REPORTING_DATASET", "pos_reporting"),
        duckdb_path=Path(env.get("DUCKDB_PATH", str(WAREHOUSE_DIR / "ksa_pos.duckdb"))),
        bq_project=project,
        bq_location=env.get("BQ_LOCATION", "US"),
        bq_api_endpoint=endpoint,
    )
