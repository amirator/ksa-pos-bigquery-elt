{{ config(tags=['heavy_join']) }}
-- The stitching test is only meaningful if releases A and B actually overlap.
with a as (select week_start from {{ ref('stg_sama_pos') }}
           where source = 'A' and sector = 'All sectors' and city = 'KSA total'),
     b as (select week_start from {{ ref('stg_sama_pos') }}
           where source = 'B' and sector = 'All sectors' and city = 'KSA total'),
     o as (select count(*) as n from a join b on a.week_start = b.week_start)
select n from o where n < 1
