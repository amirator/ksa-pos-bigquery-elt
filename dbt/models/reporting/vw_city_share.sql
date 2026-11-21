-- Each named city's share of national POS value per full calendar year,
-- its average ticket, and its share change against the first full year.
with nat as (
    select extract(year from week_start) as year, count(*) as weeks, sum(txn_value_k_sar) as nat_value
    from {{ ref('fct_pos_national_weekly') }}
    group by extract(year from week_start)
),
cy as (
    select d.city_name, d.admin_region, extract(year from f.week_start) as year,
           count(*) as weeks, sum(f.txn_value_k_sar) as city_value, sum(f.txn_count_k) as city_count
    from {{ ref('fct_pos_city_weekly') }} f
    join {{ ref('dim_city') }} d on d.city_key = f.city_key
    group by d.city_name, d.admin_region, extract(year from f.week_start)
),
joined as (
    select cy.city_name, cy.admin_region, cy.year, cy.weeks,
           cy.city_value / 1e6                                           as value_bn_sar,
           100 * cy.city_value / nat.nat_value                           as share_pct,
           {{ safe_divide('cy.city_value', 'cy.city_count') }}           as avg_ticket_sar
    from cy
    join nat on nat.year = cy.year
    where nat.weeks >= 52
)
select
    city_name, admin_region, year, weeks, value_bn_sar, share_pct, avg_ticket_sar,
    share_pct - first_value(share_pct) over (partition by city_name order by year
                                             rows between unbounded preceding and unbounded following)
                                                                         as share_change_vs_first_year_pp,
    rank() over (partition by year order by share_pct desc)              as share_rank
from joined
