from django import template

register = template.Library()


@register.filter
def format_price(value):
    try:
        return f"{int(value) / 100:.2f} CHF"
    except (ValueError, TypeError):
        return "Invalid price"


register.filter("format_price", format_price)
