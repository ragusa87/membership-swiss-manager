from django.db import models
from django.utils.translation import gettext_lazy as _


class SubscriptionTypeEnum(models.TextChoices):
    MEMBER = "MEMBER", _("Member")
    SUPPORTER = "SUPPORTER", _("Supporter")


class Subscription(models.Model):
    name = models.CharField(max_length=255)
    price_member = models.IntegerField(default=6000)
    price_supporter = models.IntegerField(default=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_price_by_type(self, subscription_type):
        if subscription_type == SubscriptionTypeEnum.MEMBER:
            return self.price_member
        elif subscription_type == SubscriptionTypeEnum.SUPPORTER:
            return self.price_supporter
        return None

    class Meta:
        db_table = "subscription"
