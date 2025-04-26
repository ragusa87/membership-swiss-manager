import json

from django import forms
from django.conf import settings


class AddressWidget(forms.TextInput):
    template_name = "myapp/widgets/address.html"

    def __init__(self, attrs=None, config=None):
        if attrs is None:
            attrs = {}
        attrs["placeholder"] = (
            "Chemin du .."
            if not attrs or "placeholder" not in attrs
            else attrs["placeholder"]
        )
        config = {
            "apiurl": settings.LOCATIONS_SEARCH_API,
            "apiurlDetail": settings.LOCATIONS_SEARCH_API_DETAILS,
            "lang": "fr",
            "field_zip": "#id_zip",
            "field_city": "#id_city",
            "field_number": "#id_address_number",
            "debug": settings.DEBUG,
            **(config or {}),
        }
        super().__init__(
            {
                "data-config": json.dumps(config),
                **(attrs or {}),
            }
        )
