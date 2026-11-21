-- Clean, harmonise and pivot the two raw SAMA extracts:
-- one row per (source, week_start, sector, city) with value and count columns.
-- Ported from sql/01_staging.sql in github.com/amirator/ksa-pos-spending-dashboard,
-- rewritten in portable SQL (conditional aggregation instead of DuckDB PIVOT).
with unioned as (
    select source, starting_date, indicator, sector_raw, city_raw, value from {{ source('pos_raw', 'sama_pos_a') }}
    union all
    select source, starting_date, indicator, sector_raw, city_raw, value from {{ source('pos_raw', 'sama_pos_b') }}
),

mapped as (
    select
        source,
        {{ snap_to_sunday('starting_date') }} as week_start,
        case indicator
            when 'Number of Transactions (In Thousand)'    then 'txn_count_k'
            when 'Value of Transactions (In Thousand SAR)' then 'txn_value_k_sar'
            when 'Number of Transactions Change %'         then 'pub_count_wow_pct'
            when 'Value of Transactions Change %'          then 'pub_value_wow_pct'
        end as metric,
        -- National totals: A uses 'Total', B uses '20.Total'
        case when sector_raw in ('Total', '20.Total') then 'All sectors' else sector_raw end as sector,
        -- Harmonise B's city spellings to A's 10 named cities
        case
            when city_raw = 'Total'                    then 'KSA total'
            when upper(city_raw) = 'RIYADH'            then 'Riyadh'
            when upper(city_raw) = 'JEDDAH'            then 'Jeddah'
            when upper(city_raw) = 'MAKKAH'            then 'Makkah'
            when upper(city_raw) = 'DAMMAM'            then 'Dammam'
            when upper(city_raw) = 'ABHA'              then 'Abha'
            when upper(city_raw) = 'BURAIDAH'          then 'Buraidah'
            when upper(city_raw) = 'TABOUK'            then 'Tabouk'
            when city_raw in ('MADINA', 'Al-Madinah')  then 'Madinah'
            when city_raw in ('KHOBAR', 'Al-Khubar')   then 'Khobar'
            when city_raw in ('HAIL', 'Hayel')         then 'Hail'
            when city_raw = 'OTHER'                    then 'Other (A only)'
            else city_raw
        end as city,
        value
    from unioned
)

select
    source,
    week_start,
    sector,
    city,
    max(case when metric = 'txn_value_k_sar'   then value end) as txn_value_k_sar,
    max(case when metric = 'txn_count_k'       then value end) as txn_count_k,
    max(case when metric = 'pub_value_wow_pct' then value end) as pub_value_wow_pct,
    max(case when metric = 'pub_count_wow_pct' then value end) as pub_count_wow_pct,
    count(*)                                                   as source_rows
from mapped
group by source, week_start, sector, city
