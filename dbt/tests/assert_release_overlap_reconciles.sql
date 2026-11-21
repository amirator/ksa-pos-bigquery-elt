{{ config(tags=['heavy_join']) }}
-- In the weeks where releases A and B overlap, KSA and city totals must agree within 0.01%.
-- This is what justifies stitching A (to Jul 2025) and B (later weeks) into one series.
with a as (select week_start, city, txn_value_k_sar as v from {{ ref('stg_sama_pos') }}
           where source = 'A' and sector = 'All sectors'),
     b as (select week_start, city, txn_value_k_sar as v from {{ ref('stg_sama_pos') }}
           where source = 'B' and sector = 'All sectors')
select a.week_start, a.city, a.v as v_a, b.v as v_b
from a
join b on a.week_start = b.week_start and a.city = b.city
where a.city in ('KSA total', 'Riyadh', 'Jeddah', 'Makkah', 'Madinah', 'Dammam', 'Khobar',
                 'Buraidah', 'Abha', 'Tabouk', 'Hail')
  and abs(a.v - b.v) > 0.0001 * a.v
