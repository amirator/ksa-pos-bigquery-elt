-- Full calendar years only (>= 52 week starts). Years are compared on AVERAGE WEEKLY
-- values because some years hold 53 week starts. Average ticket = value / count.
with y as (
    select
        extract(year from week_start)                                 as year,
        count(*)                                                      as weeks,
        sum(txn_value_k_sar) / 1e6                                    as value_bn_sar,
        avg(txn_value_k_sar) / 1e6                                    as avg_weekly_value_bn_sar,
        avg(txn_count_k) / 1e3                                        as avg_weekly_txn_mn,
        {{ safe_divide('sum(txn_value_k_sar)', 'sum(txn_count_k)') }} as avg_ticket_sar
    from {{ ref('fct_pos_national_weekly') }}
    group by extract(year from week_start)
)
select
    year, weeks, value_bn_sar, avg_weekly_value_bn_sar, avg_weekly_txn_mn, avg_ticket_sar,
    100 * ({{ safe_divide('avg_weekly_value_bn_sar', 'lag(avg_weekly_value_bn_sar) over (order by year)') }} - 1) as value_yoy_pct,
    100 * ({{ safe_divide('avg_weekly_txn_mn', 'lag(avg_weekly_txn_mn) over (order by year)') }} - 1)             as txn_yoy_pct,
    100 * ({{ safe_divide('avg_ticket_sar', 'lag(avg_ticket_sar) over (order by year)') }} - 1)                   as ticket_yoy_pct
from y
where weeks >= 52
