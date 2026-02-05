from django.forms import fields, NumberInput


class PriceInput(NumberInput):
    template_name = "core/widgets/price.html"


class PriceField(fields.IntegerField):
    widget = PriceInput

    def prepare_value(self, value):
        return str(int(value / 100)) if value else None

    def to_python(self, value):
        return int(value) * 100 if str(value).strip() != "" else None
