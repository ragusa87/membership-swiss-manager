from django import template

register = template.Library()


@register.filter
def format_price(value, currency="CHF"):
    if value == 0 or value is None:
        return "0.00 %s" % currency
    try:
        return f"{int(value) / 100:.2f} {currency}"
    except (ValueError, TypeError):
        return "Invalid price %s" % str(value)


@register.inclusion_tag("myapp/partials/sprite.html")
def sprite(sprite_name: str, sprite_size=24):
    return {
        "sprite_name": sprite_name,
        "sprite_size": sprite_size,
    }
