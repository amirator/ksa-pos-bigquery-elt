-- KSA total, all sectors. Release A up to its last week, then release B for later weeks
-- (A and B agree to within 0.01% in the overlap; see tests/assert_release_overlap_reconciles.sql).
with cutover as (
    select max(week_start) as last_week_a from {{ ref('stg_sama_pos') }} where source = 'A'
)
select s.week_start, s.source, s.txn_value_k_sar, s.txn_count_k
from {{ ref('stg_sama_pos') }} s
cross join cutover c
where s.sector = 'All sectors' and s.city = 'KSA total'
  and (s.source = 'A' or (s.source = 'B' and s.week_start > c.last_week_a))
