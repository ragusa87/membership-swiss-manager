from django import template

register = template.Library()


@register.filter
def format_price(value):
    if value == 0 or value is None:
        return "0.00 CHF"
    try:
        return f"{int(value) / 100:.2f} CHF"
    except (ValueError, TypeError):
        return "Invalid price %s" % str(value)


register.filter("format_price", format_price)


@register.inclusion_tag("myapp/partials/sprite.html")
def sprite(sprite_name: str, sprite_size=24):
    return {
        "sprite_name": sprite_name,
        "sprite_size": sprite_size,
    }
