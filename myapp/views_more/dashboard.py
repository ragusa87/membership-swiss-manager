from django.shortcuts import get_object_or_404
from myapp.models import Invoice, MemberSubscription, Subscription, InvoiceStatusEnum
from django.views.generic import TemplateView
from datetime import datetime
from django.db.models import Sum


class DashboardView(TemplateView):
    template_name = "myapp/dashboard.html"

    def get_context_data(self, **kwargs):
        subscription_name = str(datetime.now().year)
        if "subscription_name" in kwargs and kwargs["subscription_name"] != "":
            subscription_name = kwargs["subscription_name"]

        subscription = get_object_or_404(Subscription, name=subscription_name)

        total_subscriptions = MemberSubscription.objects.filter(
            subscription=subscription
        ).count()

        member_subscriptions = MemberSubscription.list_for_dashboard(subscription)

        # Calculate statistics
        previous_subscription = (
            Subscription.objects.filter(created_at__lt=subscription.created_at)
            .order_by("created_at")
            .first()
        )
        total_subscriptions_last_year = 0
        if previous_subscription is not None:
            total_subscriptions_last_year = MemberSubscription.objects.filter(
                subscription=previous_subscription,
            ).count()

        # Calculate subscription growth
        if total_subscriptions_last_year > 0:
            subscription_growth = (
                (total_subscriptions - total_subscriptions_last_year)
                / total_subscriptions_last_year
                * 100
            )
        else:
            subscription_growth = 100

        # Calculate amounts
        current_due_amount = (
            Invoice.objects.filter(
                member_subscription__subscription=subscription,
                member_subscription__parent__subscription=None,
                member_subscription__active=True,
                status__in=(InvoiceStatusEnum.CREATED, InvoiceStatusEnum.PENDING),
            ).aggregate(total=Sum("price"))["total"]
            or 0
        )

        last_year_due_amount = (
            Invoice.objects.filter(
                member_subscription__subscription=previous_subscription,
                member_subscription__parent__subscription=None,
                member_subscription__active=True,
                status__in=(InvoiceStatusEnum.CREATED, InvoiceStatusEnum.PENDING),
            ).aggregate(total=Sum("price"))["total"]
            or 0
        )

        due_amount_growth = (
            ((current_due_amount - last_year_due_amount) / last_year_due_amount * 100)
            if last_year_due_amount > 0
            else 0
        )

        paid_amount = (
            Invoice.objects.filter(
                status="paid",
                member_subscription__subscription=subscription,
            ).aggregate(total=Sum("price"))["total"]
            or 0
        )

        due_amounts = (
            MemberSubscription.objects.filter(
                subscription=subscription,
                active=True,
            ).aggregate(total=Sum("price"))["total"]
            or 0
        )

        # Calculate rates
        collection_rate = (paid_amount / due_amounts * 100) if due_amounts > 0 else 0

        active_users = (
            MemberSubscription.objects.filter(
                active=True,
                parent__subscription=None,
                subscription=subscription,
            )
            .values("member_id")
            .distinct()
            .count()
        )

        total_users = (
            MemberSubscription.objects.filter(
                active=True,
                subscription=subscription,
            )
            .values("member_id")
            .distinct()
            .count()
        )
        retention_rate = (active_users / total_users * 100) if total_users > 0 else 0

        # Get recent subscriptions
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "subscription": subscription,
                "InvoiceStatusEnum": InvoiceStatusEnum,
                "stats": {
                    "total_subscriptions": total_subscriptions,
                    "total_subscriptions_last_year": total_subscriptions_last_year,
                    "subscription_growth": round(subscription_growth, 1),
                    "due_amount": current_due_amount,
                    "due_amount_growth": round(due_amount_growth, 1),
                    "paid_amount": paid_amount,
                    "collection_rate": round(collection_rate, 1),
                    "active_users": active_users,
                    "retention_rate": round(retention_rate, 1),
                    "last_year_due_amount": last_year_due_amount,
                    "total_users": total_users,
                },
                "member_subscriptions": member_subscriptions,
            }
        )
        return context
