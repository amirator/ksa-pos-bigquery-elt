-- 10 named cities, all sectors, same A-then-B stitching rule as the national fact.
with cutover as (
    select max(week_start) as last_week_a from {{ ref('stg_sama_pos') }} where source = 'A'
)
select s.week_start, d.city_key, s.source, s.txn_value_k_sar, s.txn_count_k
from {{ ref('stg_sama_pos') }} s
join {{ ref('dim_city') }} d on d.city_name = s.city
cross join cutover c
where s.sector = 'All sectors'
  and (s.source = 'A' or (s.source = 'B' and s.week_start > c.last_week_a))
