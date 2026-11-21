{% test is_sunday(model, column_name) %}
select {{ column_name }}
from {{ model }}
where {{ dow_sun0(column_name) }} <> 0
{% endtest %}
