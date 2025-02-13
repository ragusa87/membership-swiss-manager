from django.db import models
from decimal import Decimal

from django.db.models import Q
from django.utils.translation import gettext as _
from django.utils.translation import ngettext


class InvoiceStatusEnum(models.TextChoices):
    CREATED = "created"
    PAID = "paid"
    PENDING = "pending"
    CANCELED = "canceled"


class Invoice(models.Model):
    reference = models.IntegerField(null=True, blank=True)
    member_subscription = models.ForeignKey(
        "MemberSubscription", on_delete=models.CASCADE, related_name="invoices"
    )
    status = models.CharField(
        max_length=10,
        choices=InvoiceStatusEnum.choices,
        default=InvoiceStatusEnum.CREATED,
    )
    reminder = models.IntegerField(default=0)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    price = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Invoice {self.get_reference()}"

    def get_reference(self):
        return self.reference if self.reference is not None else self.id

    def is_reminder(self):
        return self.reminder > 0

    def price_decimal(self):
        return Decimal(self.price) / Decimal(100)

    def get_status_text(self):
        map = {
            InvoiceStatusEnum.CREATED: _("InvoiceStatusEnum.CREATED"),
            InvoiceStatusEnum.CANCELED: _("InvoiceStatusEnum.CANCELED"),
            InvoiceStatusEnum.PAID: _("InvoiceStatusEnum.PAID"),
            InvoiceStatusEnum.PENDING: _("InvoiceStatusEnum.PENDING"),
        }
        if self.status not in map:
            return _("InvoiceStatusEnum.UNKNOWN")

        return map[self.status]

    def get_reminder_text(self):

        # Special cases for 1st, 2nd, 3rd
        reminder_text = {
            0: _("No reminder"),
            1: _("1st reminder"),
            2: _("2nd reminder"),
            3: _("3rd reminder"),
        }

        if self.reminder in reminder_text:
            return reminder_text[self.reminder]

        # General case for 4th, 5th, etc.
        return ngettext("%dth reminder", "%dth reminder", self.reminder) % self.reminder

    def create_reminder(self):
        self.status = InvoiceStatusEnum.CANCELED
        self.save()
        invoice = self
        invoice.pk = None
        invoice.reference = None
        invoice.created_at = None
        invoice.status = InvoiceStatusEnum.CREATED
        invoice.reminder = invoice.reminder + 1 if invoice.reminder is not None else 1
        invoice.save()

        return invoice

    class Meta:
        db_table = "invoice"
        constraints = [
            models.UniqueConstraint(
                fields=["reference"],
                name="unique_reference",
            )
        ]
