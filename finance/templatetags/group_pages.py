from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def group_page_url(context, key, number):
    query = context['request'].GET.copy()
    query[key] = number
    return '?' + query.urlencode()
