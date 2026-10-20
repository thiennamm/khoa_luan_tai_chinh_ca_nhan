from decimal import Decimal
from django import template

register = template.Library()


@register.filter
def vnd(value):
    if value is None:
        value = Decimal("0")
    return f"{value:,.0f}".replace(",", ".") + " ₫"
