-- The stitched weekly series must have no gaps: one row for every Sunday between first and last week.
with b as (
    select min(week_start) as lo, max(week_start) as hi, count(*) as n
    from {{ ref('fct_pos_national_weekly') }}
)
select lo, hi, n from b
where n <> cast({{ dbt.datediff('lo', 'hi', 'day') }} / 7 as {{ dbt.type_int() }}) + 1
