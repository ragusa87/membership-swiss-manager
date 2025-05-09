from django import template
from django.conf import settings

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


@register.filter(name="add_class")
def add_class(field, css):
    return field.as_widget(attrs={**field.field.widget.attrs, "class": css})


@register.inclusion_tag("myapp/partials/authentication_demo.html")
def authentication_demo():
    return {
        "authentication_demo_enabled": settings.CUSTOM_AUTHENTICATION_BACKEND == "demo"
    }
