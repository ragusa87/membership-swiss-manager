from django.db import models


class Subscription(models.Model):
    name = models.CharField(max_length=255)
    price_member = models.IntegerField(default=6000)
    price_supporter = models.IntegerField(default=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "subscription"
