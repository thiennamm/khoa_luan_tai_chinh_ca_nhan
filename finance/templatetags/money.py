from django import template
from finance.money import format_vnd

register = template.Library()


@register.filter
def vnd(value):
    return format_vnd(value)
