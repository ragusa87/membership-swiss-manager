from django.db import models
from django.utils.timezone import now

class InvoiceStatusEnum(models.TextChoices):
    CREATED = 'created'
    PAID = 'paid'
    PENDING = 'pending'
    CANCELED = 'canceled'

class Invoice(models.Model):
    reference = models.IntegerField(null=True, blank=True)
    member_subscription = models.ForeignKey(
        'MemberSubscription', on_delete=models.CASCADE, related_name='invoices'
    )
    status = models.CharField(
        max_length=10, choices=InvoiceStatusEnum.choices, default=InvoiceStatusEnum.CREATED
    )
    reminder = models.IntegerField(default=0)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice {self.id} - Status: {self.status}"

    def get_reference(self):
        return self.reference if self.reference is not None else self.id

    def is_reminder(self):
        return self.reminder > 0
    class Meta:
        db_table = "invoice"

