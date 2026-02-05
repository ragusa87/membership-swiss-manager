from collections import OrderedDict

from django import forms
from phonenumber_field.formfields import PhoneNumberField
from core.forms.autocomplete import AddressWidget
from core.models import MemberSubscription, Member


class MemberForm(forms.ModelForm):
    phone = PhoneNumberField(
        region="CH",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "+41 7x xxx xx xx"}),
    )

    class Meta:
        model = Member
        fields = [
            "firstname",
            "lastname",
            "email",
            "phone",
            "address",
            "address_number",
            "city",
            "zip",
        ]
        exclude = ["created_at", "updated_at"]
        widgets = {
            "firstname": forms.TextInput(attrs={"placeholder": "Frederic"}),
            "lastname": forms.TextInput(attrs={"placeholder": "Dupont"}),
            "email": forms.TextInput(attrs={"placeholder": "me@example.com"}),
            "address": AddressWidget(attrs=dict(placeholder="Chemin du Vanil")),
            "address_number": forms.TextInput(attrs={"placeholder": "10"}),
            "city": forms.TextInput(attrs={"placeholder": "Lausanne"}),
            "zip": forms.TextInput(attrs={"placeholder": "1006"}),
        }


class MemberSubscriptionUserForm(forms.ModelForm):
    member = forms.CharField(
        widget=forms.TextInput(attrs={"readonly": "readonly", "disabled": "disabled"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = MemberSubscription.objects.filter(
            active=True, subscription=self.instance.subscription
        )
        self.fields["member"].disabled = True
        self.fields = OrderedDict(
            [("member", self.fields.pop("member"))] + list(self.fields.items())
        )

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get("parent")
        if parent is None:
            return cleaned_data

        if parent == self.instance:
            raise forms.ValidationError("You cannot assign a subscription to itself.")

        if parent.type != cleaned_data.get("type"):
            cleaned_data["type"] = parent.type

        return cleaned_data

    class Meta:
        model = MemberSubscription
        fields = ["type", "parent"]
