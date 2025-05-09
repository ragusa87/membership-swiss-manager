from django.forms import ModelForm

from myapp.forms.price_field import PriceField
from myapp.models import Subscription


class SubscriptionForm(ModelForm):
    price_member = PriceField()
    price_supporter = PriceField()

    class Meta:
        model = Subscription
        fields = "__all__"
