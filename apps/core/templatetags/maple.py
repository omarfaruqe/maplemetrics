from django import template

from apps.core.localize import geography_name

register = template.Library()


@register.filter(name="geography")
def geography_filter(name: str) -> str:
    return geography_name(name)
