"""Read the 5 reporting views back from the warehouse -> CSVs, kpis.json and charts.

Every number in the README comes from outputs/kpis.json, which is built here from the views.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .config import DOCS_IMG, OUTPUTS, REPORTING_VIEWS
from .warehouse import Warehouse

SORT_KEYS = {
    "vw_weekly_kpis": ["week_start"],
    "vw_yearly_avg_ticket": ["year"],
    "vw_city_share": ["year", "share_rank", "city_name"],
    "vw_ramadan_eid_lift": ["year"],
    "vw_latest_vs_prior_year": ["cur_from"],
}


def read_views(wh: Warehouse, dataset: str) -> dict[str, pd.DataFrame]:
    out = {}
    for v in REPORTING_VIEWS:
        df = wh.query_df(f"SELECT * FROM {wh.fq(dataset, v)}")
        out[v] = df.sort_values(SORT_KEYS[v], kind="stable").reset_index(drop=True)
    return out


def write_csvs(views: dict[str, pd.DataFrame], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in views.items():
        df.to_csv(out_dir / f"{name}.csv", index=False, float_format="%.6f")


def _r(x, n=2):
    return None if pd.isna(x) else round(float(x), n)


def build_kpis(views: dict[str, pd.DataFrame], raw_rows: dict[str, int]) -> dict:
    wk = views["vw_weekly_kpis"]
    yr = views["vw_yearly_avg_ticket"].set_index("year")
    cs = views["vw_city_share"]
    rl = views["vw_ramadan_eid_lift"]
    lt = views["vw_latest_vs_prior_year"].iloc[0]
    y0, y1 = int(yr.index.min()), int(yr.index.max())

    def share(city, year):
        return _r(cs[(cs.city_name == city) & (cs.year == year)].share_pct.iloc[0], 1)

    return {
        "coverage": {
            "first_week": str(pd.Timestamp(wk.week_start.min()).date()),
            "last_week": str(pd.Timestamp(wk.week_start.max()).date()),
            "weeks": int(len(wk)),
            "weeks_from_release_b": int((wk.source == "B").sum()),
            "full_years": [int(y) for y in yr.index],
        },
        "raw_rows": raw_rows,
        "yearly": {
            "first_full_year": y0,
            "last_full_year": y1,
            "avg_weekly_value_bn_sar_first": _r(yr.loc[y0, "avg_weekly_value_bn_sar"]),
            "avg_weekly_value_bn_sar_last": _r(yr.loc[y1, "avg_weekly_value_bn_sar"]),
            "value_growth_pct": _r(100 * (yr.loc[y1, "avg_weekly_value_bn_sar"] / yr.loc[y0, "avg_weekly_value_bn_sar"] - 1), 1),
            "txn_growth_pct": _r(100 * (yr.loc[y1, "avg_weekly_txn_mn"] / yr.loc[y0, "avg_weekly_txn_mn"] - 1), 1),
            "avg_ticket_sar_first": _r(yr.loc[y0, "avg_ticket_sar"], 1),
            "avg_ticket_sar_last": _r(yr.loc[y1, "avg_ticket_sar"], 1),
            "avg_ticket_change_pct": _r(100 * (yr.loc[y1, "avg_ticket_sar"] / yr.loc[y0, "avg_ticket_sar"] - 1), 1),
            "value_yoy_pct_by_year": {int(y): _r(v, 1) for y, v in yr.value_yoy_pct.items() if pd.notna(v)},
        },
        "city_share": {
            "riyadh_first": share("Riyadh", y0), "riyadh_last": share("Riyadh", y1),
            "jeddah_first": share("Jeddah", y0), "jeddah_last": share("Jeddah", y1),
        },
        "ramadan_eid": {
            "years": [int(y) for y in rl.year],
            "peak_index_min": _r(rl.peak_week_index.min(), 0),
            "peak_index_median": _r(rl.peak_week_index.median(), 0),
            "peak_index_max": _r(rl.peak_week_index.max(), 0),
            "post_eid_index_min": _r(rl.post_eid_week_index.min(), 0),
            "post_eid_index_max": _r(rl.post_eid_week_index.max(), 0),
        },
        "latest_ytd": {
            "from": str(pd.Timestamp(lt.cur_from).date()),
            "to": str(pd.Timestamp(lt.cur_to).date()),
            "weeks": int(lt.weeks),
            "value_yoy_pct": _r(lt.value_yoy_pct, 1),
            "txn_yoy_pct": _r(lt.txn_yoy_pct, 1),
        },
    }


def make_charts(views: dict[str, pd.DataFrame], out_dir: Path = DOCS_IMG) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    green, gold, grey, red = "#0B6E4F", "#C8A75B", "#7B8794", "#B23A48"
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "savefig.dpi": 130, "svg.hashsalt": "ksa-pos"})
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    wk = views["vw_weekly_kpis"].copy()
    wk["week_start"] = pd.to_datetime(wk.week_start)
    yr = views["vw_yearly_avg_ticket"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [2.2, 1]})
    ax = axes[0]
    for _, r in wk[wk.is_ramadan_week.astype(bool)].iterrows():
        ax.axvspan(r.week_start, r.week_start + pd.Timedelta(days=7), color=gold, alpha=0.25, lw=0)
    ax.plot(wk.week_start, wk.value_bn_sar, color=grey, lw=0.8, label="weekly")
    ax.plot(wk.week_start, wk.value_bn_sar_4wk_avg, color=green, lw=2, label="4-week average")
    ax.set_title("vw_weekly_kpis: POS spending, SAR bn per week (gold = Ramadan weeks)")
    ax.legend(frameon=False, loc="upper left")
    ax = axes[1]
    ax.bar(yr.year.astype(str), yr.avg_ticket_sar, color=green)
    for x, v in zip(yr.year.astype(str), yr.avg_ticket_sar):
        ax.text(x, v + 1, f"{v:.1f}", ha="center")
    ax.set_title("vw_yearly_avg_ticket: SAR per transaction")
    fig.tight_layout()
    p = out_dir / "weekly_kpis_and_avg_ticket.png"
    fig.savefig(p, metadata={"Software": None})
    plt.close(fig)
    paths.append(p)

    cs = views["vw_city_share"]
    y0, y1 = int(cs.year.min()), int(cs.year.max())
    a = cs[cs.year == y0].set_index("city_name").share_pct
    b = cs[cs.year == y1].set_index("city_name").share_pct.sort_values()
    rl = views["vw_ramadan_eid_lift"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    ax = axes[0]
    idx = range(len(b))
    ax.barh([i + 0.2 for i in idx], a.reindex(b.index), height=0.4, color=grey, label=str(y0))
    ax.barh([i - 0.2 for i in idx], b, height=0.4, color=green, label=str(y1))
    ax.set_yticks(list(idx), b.index)
    ax.set_title(f"vw_city_share: share of national POS value, % ({y0} vs {y1})")
    ax.legend(frameon=False, loc="lower right")
    ax = axes[1]
    x = rl.year.astype(str)
    ax.axhline(100, color=grey, lw=1, ls="--")
    ax.bar([i - 0.2 for i in range(len(x))], rl.peak_week_index, width=0.4, color=green, label="peak Ramadan/Eid week")
    ax.bar([i + 0.2 for i in range(len(x))], rl.post_eid_week_index, width=0.4, color=red, label="week after Eid")
    ax.set_xticks(range(len(x)), x)
    ax.set_title("vw_ramadan_eid_lift: index, 4 weeks pre-Ramadan = 100")
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    fig.tight_layout()
    p = out_dir / "city_share_and_ramadan_lift.png"
    fig.savefig(p, metadata={"Software": None})
    plt.close(fig)
    paths.append(p)
    return paths


def write_kpis(kpis: dict, path: Path = OUTPUTS / "kpis.json") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(kpis, indent=2) + "\n")
