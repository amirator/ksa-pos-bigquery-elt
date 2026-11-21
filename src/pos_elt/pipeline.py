"""End-to-end ELT run.

    python -m pos_elt.pipeline                       # local DuckDB (default, no account)
    WAREHOUSE=bq-emulator python -m pos_elt.pipeline # local BigQuery emulator
    WAREHOUSE=bigquery BQ_PROJECT=my-project GOOGLE_APPLICATION_CREDENTIALS=key.json python -m pos_elt.pipeline

Steps: download (KAPSARC API) -> load raw (load jobs) -> dbt build (staging, marts, 5 views
+ tests) -> source freshness -> export views to CSV (+ kpis.json, charts, lineage for DuckDB).
"""
from __future__ import annotations

import argparse
import sys

from .config import DATASETS, DBT_DIR, DOCS_IMG, OUTPUTS, settings_from_env
from .download import download_all
from .load import load_all
from .warehouse import get_warehouse

DBT_DATASETS = ["pos_staging", "pos_marts", "pos_reporting"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--warehouse", choices=["duckdb", "bigquery", "bq-emulator"], default=None,
                    help="overrides the WAREHOUSE env var (default duckdb)")
    ap.add_argument("--offline", action="store_true", help="use the CSVs already in data/raw")
    ap.add_argument("--refresh", action="store_true", help="force a fresh download from KAPSARC")
    ap.add_argument("--force-load", action="store_true", help="reload raw tables even if file hashes are unchanged")
    args = ap.parse_args(argv)

    s = settings_from_env(args.warehouse)
    print(f"[pipeline] warehouse={s.kind} dbt_target={s.dbt_target}"
          + (f" project={s.bq_project}" if s.kind != "duckdb" else f" path={s.duckdb_path.name}"))

    if not args.offline:
        download_all(force=args.refresh)

    wh = get_warehouse(s)
    _, load_ok = load_all(wh, force=args.force_load)
    raw_rows = {
        meta["raw_table"]: int(wh.query_df(f"SELECT count(*) AS n FROM {wh.fq(s.raw_dataset, meta['raw_table'])}").iloc[0, 0])
        for meta in DATASETS.values()
    }
    if s.kind != "duckdb":
        for d in DBT_DATASETS:  # create datasets via the API (sets the location explicitly)
            wh.ensure_dataset(d)
    if s.kind == "duckdb":
        wh.close()  # release the file lock for dbt

    from .dbt_runner import run_dbt
    import os

    os.environ.update({"DUCKDB_PATH": str(s.duckdb_path), "RAW_DATASET": s.raw_dataset,
                       "BQ_LOCATION": s.bq_location})
    if s.bq_project:
        os.environ["BQ_PROJECT"] = s.bq_project
    if s.bq_api_endpoint:
        os.environ["BQ_API_ENDPOINT"] = s.bq_api_endpoint

    build_args = ["build"]
    if s.kind == "bq-emulator":
        # the SQLite-backed emulator is very slow on un-indexed joins; those reconciliation
        # tests run on DuckDB and on real BigQuery instead
        build_args += ["--exclude", "tag:heavy_join"]
    dbt_ok = run_dbt(build_args, s.dbt_target)
    fresh_ok = True
    if dbt_ok and s.kind != "bq-emulator":
        fresh_ok = run_dbt(["source", "freshness"], s.dbt_target)
    if not dbt_ok:
        print("[pipeline] dbt build failed")
        return 1

    from .export import build_kpis, make_charts, read_views, write_csvs, write_kpis

    wh = get_warehouse(s)
    views = read_views(wh, s.reporting_dataset)
    out_dir = OUTPUTS if s.kind == "duckdb" else OUTPUTS / s.dbt_target
    write_csvs(views, out_dir)
    if s.kind == "duckdb":
        write_kpis(build_kpis(views, raw_rows))
        make_charts(views)
        from .lineage import draw_lineage

        draw_lineage(DBT_DIR / "target" / "duckdb" / "manifest.json", DOCS_IMG / "dbt_lineage.png")
    wh.close()
    print(f"[pipeline] exported {len(views)} views -> {out_dir.relative_to(OUTPUTS.parent)}")
    ok = load_ok and dbt_ok and fresh_ok
    print("[pipeline] DONE" if ok else "[pipeline] finished with errors")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
