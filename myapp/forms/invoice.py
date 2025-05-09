from django.forms import ModelForm

from myapp.forms.price_field import PriceField
from myapp.models import Invoice


class InvoiceForm(ModelForm):
    price = PriceField()

    class Meta:
        model = Invoice
        fields = "__all__"
