from django.db import models
from django.db.models import Count
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
    price = models.IntegerField(
        null=True, blank=True, help_text="The price is calculated automatically."
    )

    class Meta:
        unique_together = ("subscription", "member")
        verbose_name = "Member Subscription"
        verbose_name_plural = "Member Subscriptions"
        db_table = "member_subscription"

    def __str__(self):
        return f"{self.member.get_fullname()} - {self.subscription.name}"

    def get_price_by_type(self, subscription_type: str) -> int | None:
        if subscription_type.lower() == SubscriptionTypeEnum.MEMBER.lower():
            return self.subscription.price_member
        elif subscription_type.lower() == "supporter":
            return self.subscription.price_supporter
        elif subscription_type.lower() == SubscriptionTypeEnum.OTHER.lower():
            return self.subscription.price_supporter
        return None

    def get_price(self):
        return self.price

    def calculate_price(self):
        """
        Calculate the price of the subscription based on its type.
        """
        if self.active is False or self.parent is not None:
            return 0
        return self.get_price_by_type(self.type)

    def get_type_text(self) -> str:
        return SubscriptionTypeEnum.get_type(self.type)

    def get_status_text(self) -> str:
        return _("active subscription") if self.active else _("inactive subscription")

    def get_due_amount(self):
        due_sum = self.price or self.calculate_price()
        for invoice in self.invoices.filter(status=InvoiceStatusEnum.PAID):
            due_sum -= invoice.price
        return due_sum

    def should_create_new_invoice(self):
        if not self.active or self.parent is not None:
            return False

        if self.get_due_amount() <= 0:
            return False

        return not self.invoices.filter(
            status__in=[InvoiceStatusEnum.CREATED, InvoiceStatusEnum.PENDING]
        ).exists()

    def generate_new_invoice(self):
        invoice = Invoice.objects.create(
            member_subscription=self,
            price=(self.get_due_amount() if self.get_due_amount() > 0 else self.price),
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

    def get_paid_amount(self) -> int:
        sum = 0
        for invoice in self.invoices.all():
            if invoice.status == InvoiceStatusEnum.PAID:
                sum += invoice.price
        return sum

    def has_due_balance(self) -> bool:
        return self.get_due_amount() > 0

    # Update the subscription's price on save
    def save(self, *args, **kwargs):
        self.price = self.calculate_price()
        super().save(*args, **kwargs)

    @staticmethod
    def list_for_dashboard(subscription: Subscription):
        return (
            MemberSubscription.objects.filter(
                subscription=subscription, active=True, parent__isnull=True
            )
            .select_related("subscription", "member", "parent")
            .annotate(invoice_count=Count("invoices"))
            .annotate(group_count=Count("children", distinct=True) + 1)
            .prefetch_related("invoices")
            .prefetch_related("children")
            .prefetch_related("children__member")
        )
