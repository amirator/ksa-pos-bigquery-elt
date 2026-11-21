-- Ramadan / Eid al-Fitr lift per year, indexed to the average of the 4 weeks before Ramadan (= 100):
--   ramadan_avg_index : average full Ramadan week
--   peak_week_index   : best week in the Ramadan-to-Eid window (pre-Eid shopping lands in the
--                       last Ramadan week or the Eid week depending on the weekday of Eid)
--   post_eid_week_index : the week after the Eid week
-- Ported from the ramadan_effect KPI in ksa-pos-spending-dashboard (arg_max replaced by
-- row_number so it also runs on BigQuery).
with s as (
    select f.week_start, f.txn_value_k_sar as v, d.is_ramadan_week, d.is_eid_fitr_week,
           d.ramadan_days_in_week,
           row_number() over (order by f.week_start) as rn
    from {{ ref('fct_pos_national_weekly') }} f
    join {{ ref('dim_date') }} d on d.week_start = f.week_start
),
marks as (
    select extract(year from week_start)                          as year,
           min(case when ramadan_days_in_week > 0 then rn end)    as rn_first,
           min(case when is_eid_fitr_week then rn end)            as rn_eid
    from s
    group by extract(year from week_start)
),
win as (
    select m.year, m.rn_first, m.rn_eid, s.rn, s.week_start, s.v, s.is_ramadan_week
    from marks m
    cross join s
    where m.rn_first > 4 and m.rn_eid is not null
      and s.rn between m.rn_first - 4 and m.rn_eid + 1
),
calc as (
    select year,
           avg(case when rn < rn_first then v end)                                     as base,
           avg(case when is_ramadan_week and rn between rn_first and rn_eid then v end) as ram_avg,
           max(case when rn between rn_first and rn_eid then v end)                    as peak,
           max(case when rn = rn_eid + 1 then v end)                                   as post_eid
    from win
    group by year
),
peak_week as (
    select year, week_start as peak_week_start,
           row_number() over (partition by year order by v desc) as r
    from win
    where rn between rn_first and rn_eid
)
select c.year,
       c.base / 1e6                as baseline_bn_sar,
       100 * c.ram_avg / c.base    as ramadan_avg_index,
       100 * c.peak / c.base       as peak_week_index,
       p.peak_week_start,
       100 * c.post_eid / c.base   as post_eid_week_index
from calc c
join peak_week p on p.year = c.year and p.r = 1
