from django.db import models

from core.models.enum import SubscriptionTypeEnum


class Subscription(models.Model):
    name = models.CharField(max_length=255)
    price_member = models.IntegerField(default=6000)
    price_supporter = models.IntegerField(default=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_price_by_type(self, subscription_type: SubscriptionTypeEnum) -> int:
        if subscription_type == SubscriptionTypeEnum.MEMBER:
            return self.price_member
        elif subscription_type == SubscriptionTypeEnum.OTHER:
            return self.price_supporter
        return 0

    def __str__(self):
        return self.name

    class Meta:
        db_table = "subscription"
