from django.forms import ModelForm

from core.forms.price_field import PriceField
from core.models import Subscription


class SubscriptionForm(ModelForm):
    price_member = PriceField()
    price_supporter = PriceField()

    class Meta:
        model = Subscription
        fields = "__all__"
