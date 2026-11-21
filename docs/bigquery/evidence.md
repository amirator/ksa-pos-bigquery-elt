# Real Google BigQuery evidence: project `ksa-pos-elt`

Queried through the BigQuery API by `scripts/bq_evidence.py` at 2026-11-21 13:11 UTC. Nothing in this file is typed by hand.

## Datasets

| dataset | location | default table expiry (days) | tables/views |
|---|---|---|---|
| pos_raw | US | 60 | 4 |
| pos_staging | US | 60 | 1 |
| pos_marts | US | 60 | 4 |
| pos_reporting | US | 60 | 5 |

## Row counts (SELECT count(*) on BigQuery)

| object | type | rows | expires |
|---|---|---|---|
| pos_raw.hijri_calendar | TABLE | 417 | 2027-01-20 |
| pos_raw.load_log | TABLE | 21 | 2027-01-19 |
| pos_raw.sama_pos_a | TABLE | 31262 | 2027-01-19 |
| pos_raw.sama_pos_b | TABLE | 14168 | 2027-01-19 |
| pos_staging.stg_sama_pos | TABLE | 11418 | 2027-01-20 |
| pos_marts.dim_city | TABLE | 10 | 2027-01-20 |
| pos_marts.dim_date | TABLE | 307 | 2027-01-20 |
| pos_marts.fct_pos_city_weekly | TABLE | 3070 | 2027-01-20 |
| pos_marts.fct_pos_national_weekly | TABLE | 307 | 2027-01-20 |
| pos_reporting.vw_city_share | VIEW | 50 | 2027-01-20 |
| pos_reporting.vw_latest_vs_prior_year | VIEW | 1 | 2027-01-20 |
| pos_reporting.vw_ramadan_eid_lift | VIEW | 6 | 2027-01-20 |
| pos_reporting.vw_weekly_kpis | VIEW | 307 | 2027-01-20 |
| pos_reporting.vw_yearly_avg_ticket | VIEW | 5 | 2027-01-20 |

## Latest load_log entries

| source_key | status | rows_loaded | finished_utc |
|---|---|---|---|
| calendar | loaded | 417 | 2026-11-21 13:10 |
| pos_b | loaded | 14168 | 2026-11-21 13:10 |
| calendar | loaded | 417 | 2026-11-21 13:10 |
| pos_a | loaded | 31262 | 2026-11-21 13:10 |
| pos_b | skipped_unchanged | 0 | 2026-11-21 13:10 |
| pos_a | skipped_unchanged | 0 | 2026-11-21 13:10 |
| calendar | loaded | 417 | 2026-11-21 13:06 |
| pos_b | skipped_unchanged | 0 | 2026-11-21 13:06 |
| pos_a | skipped_unchanged | 0 | 2026-11-21 13:06 |

## Sample: `pos_reporting.vw_weekly_kpis` (latest 8 weeks)

| week_start | source | value_bn_sar | txn_mn | avg_ticket_sar | vs_52wk_pct | is_ramadan_week |
|---|---|---|---|---|---|---|
| 2026-03-22 | B | 12.97 | 219.80 | 59.00 | -35.50 | False |
| 2026-03-15 | B | 14.79 | 223.90 | 66.07 | 2.20 | True |
| 2026-03-08 | B | 16.15 | 226.90 | 71.16 | 18.50 | True |
| 2026-03-01 | B | 16.14 | 226.20 | 71.33 | 23.20 | True |
| 2026-02-22 | B | 14.53 | 210.50 | 69.03 | -17.30 | True |
| 2026-02-15 | B | 13.90 | 220.60 | 63.04 | 6.60 | True |
| 2026-02-08 | B | 15.34 | 252.10 | 60.84 | 15.10 | False |
| 2026-02-01 | B | 16.11 | 256.20 | 62.87 | 17.30 | False |
