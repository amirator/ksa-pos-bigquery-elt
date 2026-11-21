"""Hijri-aware weekly calendar (Sunday week starts) with Ramadan / Eid flags.

Ported from github.com/amirator/ksa-pos-spending-dashboard (build_dim_date in transform.py).
Flags come from the Umm al-Qura calendar via `hijridate`, not hand-typed dates.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from hijridate import Gregorian

CALENDAR_START = date(2020, 1, 5)   # first Sunday of 2020
CALENDAR_END = date(2027, 12, 26)   # last Sunday of 2027


def build_calendar(start: date = CALENDAR_START, end: date = CALENDAR_END) -> pd.DataFrame:
    if start.weekday() != 6:
        raise ValueError("calendar must start on a Sunday")
    rows = []
    wk = start
    while wk <= end:
        days = [wk + timedelta(days=i) for i in range(7)]
        hij = [Gregorian(d.year, d.month, d.day).to_hijri() for d in days]
        ramadan_days = sum(h.month == 9 for h in hij)
        rows.append(
            {
                "week_start": wk,
                "week_end": wk + timedelta(days=6),
                "year": wk.year,
                "quarter": (wk.month - 1) // 3 + 1,
                "month": wk.month,
                "hijri_year": hij[0].year,
                "hijri_month": hij[0].month,
                "ramadan_days_in_week": ramadan_days,
                "is_ramadan_week": ramadan_days >= 4,
                "is_eid_fitr_week": any(h.month == 10 and h.day == 1 for h in hij),
                "is_eid_adha_week": any(h.month == 12 and h.day == 10 for h in hij),
                "is_national_day_week": any(d.month == 9 and d.day == 23 for d in days),
                "is_founding_day_week": any(d.month == 2 and d.day == 22 for d in days),
            }
        )
        wk += timedelta(days=7)
    df = pd.DataFrame(rows)
    for c in ["year", "quarter", "month", "hijri_year", "hijri_month", "ramadan_days_in_week"]:
        df[c] = df[c].astype("int64")
    return df
