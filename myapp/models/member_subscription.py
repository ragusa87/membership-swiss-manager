from django.db import models
from django.utils.translation import gettext_lazy as _
from .member import Member
from .invoice import Invoice, InvoiceStatusEnum
from .subscription import Subscription


class SubscriptionTypeEnum(models.TextChoices):
    MEMBER = "member", _("subscription.member")
    OTHER = "other", _("subscription.other")  # Add other types as needed

    @classmethod
    def get_type(self, name: str) -> str:
        """Returns the translated label for a given choice value."""
        return dict(self.choices).get(name, _("subscription.unknown"))


class MemberSubscription(models.Model):
    type = models.CharField(
        max_length=255,
        choices=SubscriptionTypeEnum.choices,
        default=SubscriptionTypeEnum.MEMBER,
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="subscriptions"
    )
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="member_subscriptions"
    )
    active = models.BooleanField(default=True)
    comment = models.TextField(null=True, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("subscription", "member")
        verbose_name = "Member Subscription"
        verbose_name_plural = "Member Subscriptions"
        db_table = "member_subscription"

    def __str__(self):
        return f"{self.member.get_fullname()} - {self.subscription.name}"

    def get_price(self):
        return self.subscription.get_price_by_type(self.type)

    def get_type_text(self) -> str:
        return SubscriptionTypeEnum.get_type(self.type)

    def get_status_text(self) -> str:
        return _("active subscription") if self.active else _("inactive subscription")

    def get_due_amount(self):
        expected = self.get_price() or 0
        paid = sum(
            invoice.price
            for invoice in self.invoices.filter(status=InvoiceStatusEnum.PAID)
            if invoice.price
        )
        return expected - paid

    def generate_new_invoice(self):
        invoice = Invoice.objects.create(
            member_subscription=self,
            price=(
                self.get_due_amount() if self.get_due_amount() > 0 else self.get_price()
            ),
            status=InvoiceStatusEnum.CREATED,
        )
        return invoice

    def needs_a_new_bill(self):
        if self.get_due_amount() > 0:
            return True
        return not self.invoices.exclude(
            status__in=[
                InvoiceStatusEnum.PAID,
                InvoiceStatusEnum.CANCELED,
            ]
        ).exists()
