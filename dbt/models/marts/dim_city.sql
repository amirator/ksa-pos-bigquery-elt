-- The 10 named cities SAMA reports in both releases, with their administrative region.
-- (A SQL model rather than a dbt seed: identical on DuckDB, BigQuery and the emulator.)
select 1  as city_key, 'Riyadh'   as city_name, 'Riyadh Region'    as admin_region union all
select 2,  'Jeddah',   'Makkah Region'    union all
select 3,  'Makkah',   'Makkah Region'    union all
select 4,  'Madinah',  'Madinah Region'   union all
select 5,  'Dammam',   'Eastern Province' union all
select 6,  'Khobar',   'Eastern Province' union all
select 7,  'Buraidah', 'Qassim Region'    union all
select 8,  'Abha',     'Asir Region'      union all
select 9,  'Tabouk',   'Tabuk Region'     union all
select 10, 'Hail',     'Hail Region'
