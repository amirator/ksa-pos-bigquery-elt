{# Use the custom schema name as-is (pos_staging, pos_marts, pos_reporting) instead of
   dbt's default "<target_schema>_<custom>" (pattern from dbt-labs/jaffle-shop). #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}{{ target.schema }}{%- else -%}{{ custom_schema_name | trim }}{%- endif -%}
{%- endmacro %}
