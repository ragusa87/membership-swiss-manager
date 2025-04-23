from collections import OrderedDict

from django import forms

from myapp.models import MemberSubscription, Member


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ["firstname", "lastname", "email"]
        exclude = ["created_at", "updated_at"]


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
