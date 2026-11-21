-- The 10 named cities can never add up to more than the national total in any year.
select year, sum(share_pct) as total_share
from {{ ref('vw_city_share') }}
group by year
having sum(share_pct) > 100
