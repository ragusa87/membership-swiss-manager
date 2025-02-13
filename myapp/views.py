from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpRequest
from myapp.models import Invoice, MemberSubscription, Subscription, InvoiceStatusEnum
from myapp.pdf_generator import PDFGenerator
from django.views.generic import TemplateView
from datetime import datetime
from django.db.models import Sum, Count, Q, Prefetch, Aggregate
from .settings import LANGUAGES

# views.py
from django.utils import translation
from django.http import HttpResponseRedirect
from django.urls import reverse


def switch_language(request):
    """
    View to change the language.
    POST `language` should be a language code like 'en', 'es', 'fr', etc.
    """
    next_url = request.META.get("HTTP_REFERER", "/")  # Go back to the referring page
    response = HttpResponseRedirect(next_url)
    lang_code = request.POST.get("language", request.GET.get("language"))
    if lang_code in dict(LANGUAGES):  # Check if the lang_code is valid
        translation.activate(lang_code)
        request.session["django_language"] = lang_code
        response.set_cookie("django_language", lang_code)

    return response


def index(request):
    last = Subscription.objects.order_by("-created_at").first()
    if last:
        return HttpResponseRedirect(
            redirect_to=reverse("dashboard", kwargs={"subscription_name": last.name})
        )
    return HttpResponse("Hello, world.")


def single_invoice(self, invoice_id: int) -> HttpResponse:
    generator = PDFGenerator()
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    pdf_output = generator.generate_pdf([invoice])
    return HttpResponse(pdf_output.read(), content_type="application/pdf")


def my_ip(request: HttpRequest) -> HttpResponse:
    list = {
        "forwarded": request.headers.get("X-Forwarded-For"),
        "remote_addr": request.META.get("REMOTE_ADDR"),
    }

    return HttpResponse(str(list), content_type="text/plain")


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

        member_subscriptions = (
            MemberSubscription.objects.filter(subscription=subscription, active=True)
            .select_related("subscription", "member", "parent")
            .annotate(invoice_count=Count("invoices"))
            .annotate(parent_count=Count("children"))
            .prefetch_related("invoices")
            .prefetch_related("children")
            .prefetch_related("children__member")
        )

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
