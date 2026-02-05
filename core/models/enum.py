from django.db import models
from django.utils.translation import gettext_lazy as _


class SubscriptionTypeEnum(models.TextChoices):
    MEMBER = "member", _("subscription.member")
    OTHER = "other", _("subscription.other")  # Add other types as needed

    @classmethod
    def get_type(self, name: str) -> str:
        """Returns the translated label for a given choice value."""
        return dict(self.choices).get(name, _("subscription.unknown"))
