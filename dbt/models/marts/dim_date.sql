-- Weekly date dimension (Sunday week starts) with Umm al-Qura Ramadan / Eid flags,
-- trimmed to the weeks covered by the facts.
with bounds as (
    select min(week_start) as lo, max(week_start) as hi from {{ ref('stg_sama_pos') }}
)
select c.*
from {{ source('pos_raw', 'hijri_calendar') }} c
cross join bounds b
where c.week_start between b.lo and b.hi
