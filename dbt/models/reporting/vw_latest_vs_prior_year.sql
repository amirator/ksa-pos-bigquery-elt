-- Year-to-date for the newest year in the data vs the same weeks 52 weeks (364 days) earlier.
with latest as (
    select max(week_start) as max_wk from {{ ref('fct_pos_national_weekly') }}
),
cur as (
    select f.week_start, f.txn_value_k_sar, f.txn_count_k
    from {{ ref('fct_pos_national_weekly') }} f
    cross join latest l
    where extract(year from f.week_start) = extract(year from l.max_wk)
),
prev as (
    select f.txn_value_k_sar, f.txn_count_k
    from {{ ref('fct_pos_national_weekly') }} f
    join cur c on f.week_start = {{ sub_days('c.week_start', 364) }}
),
c_agg as (
    select min(week_start) as cur_from, max(week_start) as cur_to, count(*) as weeks,
           sum(txn_value_k_sar) as cur_v, sum(txn_count_k) as cur_n
    from cur
),
p_agg as (
    select count(*) as prev_weeks, sum(txn_value_k_sar) as prev_v, sum(txn_count_k) as prev_n
    from prev
)
select cur_from, cur_to, weeks, prev_weeks,
       cur_v / 1e6                                       as cur_value_bn_sar,
       prev_v / 1e6                                      as prev_value_bn_sar,
       100 * ({{ safe_divide('cur_v', 'prev_v') }} - 1)  as value_yoy_pct,
       100 * ({{ safe_divide('cur_n', 'prev_n') }} - 1)  as txn_yoy_pct,
       {{ safe_divide('cur_v', 'cur_n') }}               as cur_avg_ticket_sar,
       {{ safe_divide('prev_v', 'prev_n') }}             as prev_avg_ticket_sar
from c_agg
cross join p_agg
