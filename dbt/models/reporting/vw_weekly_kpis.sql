-- Weekly national KPIs: value, volume, average ticket, 4-week rolling average,
-- week-on-week and same-week-last-year change, with Ramadan / Eid flags.
-- Units out: SAR billions, millions of transactions, SAR per transaction.
select
    f.week_start,
    extract(year from f.week_start)                                        as year,
    f.source,
    f.txn_value_k_sar / 1e6                                                as value_bn_sar,
    f.txn_count_k / 1e3                                                    as txn_mn,
    {{ safe_divide('f.txn_value_k_sar', 'f.txn_count_k') }}                as avg_ticket_sar,
    avg(f.txn_value_k_sar / 1e6) over (order by f.week_start rows between 3 preceding and current row)
                                                                           as value_bn_sar_4wk_avg,
    100 * ({{ safe_divide('f.txn_value_k_sar', 'lag(f.txn_value_k_sar) over (order by f.week_start)') }} - 1)
                                                                           as value_wow_pct,
    100 * ({{ safe_divide('f.txn_value_k_sar', 'lag(f.txn_value_k_sar, 52) over (order by f.week_start)') }} - 1)
                                                                           as value_vs_52wk_ago_pct,
    d.is_ramadan_week,
    d.is_eid_fitr_week,
    d.is_eid_adha_week
from {{ ref('fct_pos_national_weekly') }} f
join {{ ref('dim_date') }} d on d.week_start = f.week_start
