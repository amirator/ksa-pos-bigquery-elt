{{ config(tags=['heavy_join']) }}
-- Reconciliation: the national fact must equal the raw KSA-total value rows it was built from
-- (A for every A week, B only after A's last week), to within SAR 1 thousand.
with cut as (
    select max(starting_date) as last_a from {{ source('pos_raw', 'sama_pos_a') }}
),
raw_total as (
    select sum(value) as v from {{ source('pos_raw', 'sama_pos_a') }}
    where indicator = 'Value of Transactions (In Thousand SAR)' and sector_raw = 'Total' and city_raw = 'Total'
    union all
    select sum(r.value) from {{ source('pos_raw', 'sama_pos_b') }} r cross join cut
    where r.indicator = 'Value of Transactions (In Thousand SAR)' and r.sector_raw = '20.Total'
      and r.city_raw = 'Total' and r.starting_date > cut.last_a
),
r as (select sum(v) as v from raw_total),
f as (select sum(txn_value_k_sar) as v from {{ ref('fct_pos_national_weekly') }})
select r.v as raw_v, f.v as fact_v from r cross join f where abs(r.v - f.v) > 1
