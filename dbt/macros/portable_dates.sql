{# Dialect-specific date helpers, dispatched by adapter so the models stay identical on
   DuckDB and BigQuery. Default implementation = BigQuery GoogleSQL.
   (No unary minus: the BigQuery emulator used in CI cannot evaluate it inside views.) #}

{# Day of week with Sunday = 0 ... Saturday = 6 #}
{% macro dow_sun0(col) %}{{ return(adapter.dispatch('dow_sun0', 'ksa_pos')(col)) }}{% endmacro %}
{% macro default__dow_sun0(col) %}(extract(dayofweek from {{ col }}) - 1){% endmacro %}
{% macro duckdb__dow_sun0(col) %}dayofweek({{ col }}){% endmacro %}

{# Add / subtract a non-negative integer number of days to a DATE, returning a DATE #}
{% macro add_days(col, n) %}{{ return(adapter.dispatch('add_days', 'ksa_pos')(col, n)) }}{% endmacro %}
{% macro default__add_days(col, n) %}date_add({{ col }}, interval cast({{ n }} as int64) day){% endmacro %}
{% macro duckdb__add_days(col, n) %}cast({{ col }} + cast({{ n }} as integer) as date){% endmacro %}

{% macro sub_days(col, n) %}{{ return(adapter.dispatch('sub_days', 'ksa_pos')(col, n)) }}{% endmacro %}
{% macro default__sub_days(col, n) %}date_sub({{ col }}, interval cast({{ n }} as int64) day){% endmacro %}
{% macro duckdb__sub_days(col, n) %}cast({{ col }} - cast({{ n }} as integer) as date){% endmacro %}

{# SAMA weeks start on Sunday; one 2020 week is stamped Saturday 2020-06-20.
   Snap every date to the NEAREST Sunday (Sun..Wed -> back, Thu..Sat -> forward). #}
{% macro snap_to_sunday(col) %}
    case when {{ dow_sun0(col) }} <= 3
         then {{ sub_days(col, dow_sun0(col)) }}
         else {{ add_days(col, '7 - ' ~ dow_sun0(col)) }}
    end
{% endmacro %}
