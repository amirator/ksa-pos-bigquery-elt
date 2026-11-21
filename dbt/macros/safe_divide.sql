{# NULL instead of a divide-by-zero error on both engines #}
{% macro safe_divide(num, den) %}(case when ({{ den }}) = 0 or ({{ den }}) is null then null else ({{ num }}) / ({{ den }}) end){% endmacro %}
