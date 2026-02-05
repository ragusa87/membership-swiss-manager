from django.db import models
from decimal import Decimal

from django.utils.translation import gettext as _
from django.utils.translation import ngettext


class InvoiceStatusEnum(models.TextChoices):
    CREATED = "created"
    PAID = "paid"
    PENDING = "pending"
    CANCELED = "canceled"

    @staticmethod
    def from_string(value: str | None) -> "InvoiceStatusEnum|None":
        if value is None:
            return None
        try:
            return InvoiceStatusEnum(value)
        except ValueError:
            return None


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

    def get_status_class(self):
        match self.status.lower():
            case InvoiceStatusEnum.PAID:
                return "bg-green-100 text-green-800"
            case InvoiceStatusEnum.CANCELED:
                return "bg-gray-100 text-gray-800"
            case InvoiceStatusEnum.PENDING:
                return "bg-yellow-100 text-yellow-800"
            case InvoiceStatusEnum.CREATED:
                return "bg-red-100 text-red-800"
            case _:
                return "bg-red-100 text-red-800"

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

    def get_amount(self) -> float:
        return float(self.price / 100 if self.price else 0.0)

    def should_split(self, price: int, transaction_id: str) -> bool:
        return (
            self.price != price
            or self.transaction_id is not None
            and self.transaction_id != transaction_id
            or self.status == InvoiceStatusEnum.PAID
        )

    def split_and_pay(self, price: int, transaction_id: str):
        self.status = InvoiceStatusEnum.PAID
        self.save()

        invoice = self
        invoice.pk = None
        invoice.reference = None
        invoice.created_at = None
        invoice.status = InvoiceStatusEnum.PAID
        invoice.reminder = self.reminder
        invoice.transaction_id = transaction_id
        invoice.price = price - self.price

        invoice.save()

        return invoice

    def can_create_reminder(self) -> bool:
        if self.reminder is not None and self.reminder >= 3:
            return False

        if self.status != InvoiceStatusEnum.PENDING:
            return False

        return True

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
