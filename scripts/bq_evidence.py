"""Query real Google BigQuery for evidence that the pipeline ran there: dataset locations and
default table expiry, row counts of every table/view, the load log, and recent vw_weekly_kpis rows.

    WAREHOUSE=bigquery BQ_PROJECT=... GOOGLE_APPLICATION_CREDENTIALS=key.json python scripts/bq_evidence.py
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pos_elt.config import settings_from_env  # noqa: E402
from pos_elt.warehouse import BigQueryWarehouse  # noqa: E402

DATASETS = ["pos_raw", "pos_staging", "pos_marts", "pos_reporting"]


def md_table(df) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join("" if v is None else (f"{v:,.2f}" if isinstance(v, float) else str(v)) for v in r) + " |")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/bigquery/evidence.md")
    args = ap.parse_args()
    s = settings_from_env("bigquery")
    wh = BigQueryWarehouse(s)
    c, p = wh.client, s.bq_project
    lines = [f"# Real Google BigQuery evidence: project `{p}`",
             "",
             f"Queried through the BigQuery API by `scripts/bq_evidence.py` at "
             f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. Nothing in this file is typed by hand.",
             "", "## Datasets", "", "| dataset | location | default table expiry (days) | tables/views |", "|---|---|---|---|"]
    counts = []
    for d in DATASETS:
        ds = c.get_dataset(f"{p}.{d}")
        exp = ds.default_table_expiration_ms
        tables = sorted(c.list_tables(ds), key=lambda t: t.table_id)
        lines.append(f"| {d} | {ds.location} | {'none' if exp is None else round(exp / 86_400_000)} | {len(tables)} |")
        for t in tables:
            n = int(wh.query_df(f"SELECT count(*) AS n FROM `{p}.{d}.{t.table_id}`").iloc[0, 0])
            full = c.get_table(t.reference)
            expires = full.expires.strftime("%Y-%m-%d") if full.expires else "-"
            counts.append({"object": f"{d}.{t.table_id}", "type": t.table_type, "rows": n, "expires": expires})
    import pandas as pd

    lines += ["", "## Row counts (SELECT count(*) on BigQuery)", "", md_table(pd.DataFrame(counts))]
    log = wh.query_df(
        f"SELECT source_key, status, rows_loaded, FORMAT_TIMESTAMP('%Y-%m-%d %H:%M', finished_at) AS finished_utc "
        f"FROM `{p}.pos_raw.load_log` ORDER BY finished_at DESC LIMIT 9")
    lines += ["", "## Latest load_log entries", "", md_table(log)]
    kpi = wh.query_df(
        f"SELECT CAST(week_start AS STRING) AS week_start, source, ROUND(value_bn_sar, 3) AS value_bn_sar, "
        f"ROUND(txn_mn, 1) AS txn_mn, ROUND(avg_ticket_sar, 2) AS avg_ticket_sar, "
        f"ROUND(value_vs_52wk_ago_pct, 1) AS vs_52wk_pct, is_ramadan_week "
        f"FROM `{p}.pos_reporting.vw_weekly_kpis` ORDER BY week_start DESC LIMIT 8")
    lines += ["", "## Sample: `pos_reporting.vw_weekly_kpis` (latest 8 weeks)", "", md_table(kpi), ""]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
