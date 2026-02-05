from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def format_price(value, currency="CHF"):
    if value == 0 or value is None:
        return "0.00 %s" % currency
    try:
        return f"{int(value) / 100:.2f} {currency}"
    except (ValueError, TypeError):
        return "Invalid price %s" % str(value)


@register.simple_tag
def sprite(sprite_name: str, sprite_size=24, **kwargs):
    class_name = "icon inline-block"
    if "class" in kwargs:
        class_name += " " + escape(str(kwargs.pop("class")))

    attrs_str = " ".join(
        f'{escape(key)}="{escape(value)}"' for key, value in kwargs.items()
    )
    return render_to_string(
        "core/partials/sprite.html",
        {
            "sprite_name": sprite_name,
            "sprite_size": int(sprite_size),
            "class_name": class_name,
            "attrs": mark_safe(attrs_str),
        },
    )


@register.filter(name="add_class")
def add_class(field, css):
    return field.as_widget(attrs={**field.field.widget.attrs, "class": css})


@register.inclusion_tag("core/partials/authentication_demo.html")
def authentication_demo():
    return {
        "authentication_demo_enabled": settings.CUSTOM_AUTHENTICATION_BACKEND == "demo"
    }
