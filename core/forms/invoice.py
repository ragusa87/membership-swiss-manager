from django.forms import ModelForm

from core.forms.price_field import PriceField
from core.models import Invoice


class InvoiceForm(ModelForm):
    price = PriceField()

    class Meta:
        model = Invoice
        fields = "__all__"
