"""Run dbt in-process for a given target.

Emulator shim (bq_emulator target ONLY): (1) goccy/bigquery-emulator returns DDL jobs
(CREATE SCHEMA / CREATE VIEW / CREATE TABLE AS) without a `destination` table, and
dbt-bigquery then calls client.get_table(None) to count rows. The shim makes that call
return "row count unknown" instead of crashing. Real BigQuery never takes this path, and
(2) the emulator does not implement routines.list, so it returns an empty list
(this project defines no BigQuery UDFs). The shim is not applied for the `bigquery` or `duckdb` targets.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

from .config import DBT_DIR

_SHIM_APPLIED = False


def apply_emulator_shim() -> None:
    global _SHIM_APPLIED
    if _SHIM_APPLIED:
        return
    from google.cloud import bigquery

    original = bigquery.Client.get_table

    def get_table(self, table, *args, **kwargs):
        if table is None:
            return SimpleNamespace(num_rows=None)
        return original(self, table, *args, **kwargs)

    bigquery.Client.get_table = get_table
    # The emulator does not implement routines.list (UDF discovery); this project has no UDFs.
    bigquery.Client.list_routines = lambda self, *a, **k: iter(())
    _SHIM_APPLIED = True


def run_dbt(args: list[str], target: str, env: dict | None = None) -> bool:
    """Invoke `dbt <args>` against `target`. Returns True on success."""
    from dbt.cli.main import dbtRunner

    if env:
        os.environ.update(env)
    os.environ["DBT_TARGET"] = target
    if target == "bq_emulator":
        apply_emulator_shim()
    full = [*args, "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR),
            "--target", target, "--target-path", f"target/{target}"]
    res = dbtRunner().invoke(full)
    return bool(res.success)
