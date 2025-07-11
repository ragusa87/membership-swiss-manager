from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from myapp.models import Invoice, Subscription, InvoiceStatusEnum, MemberSubscription
from myapp.pdf_generator import PDFGenerator
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


@login_required
def pdf_by_invoice(request, invoice_id: int) -> HttpResponse:
    generator = PDFGenerator()
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    pdf_output = generator.generate_pdf([invoice])
    return HttpResponse(pdf_output.read(), content_type="application/pdf")


@login_required
def pdfs_by_subscription(request, subscription_id: int) -> HttpResponse:
    subscription = get_object_or_404(Subscription, pk=subscription_id)
    filter_raw = request.GET.get("status", None)
    status = InvoiceStatusEnum.from_string(filter_raw)
    url_filter = (
        Q(status=status)
        if status is not None
        else Q(status__in=[InvoiceStatusEnum.CREATED])
    )

    invoices = Invoice.objects.filter(
        Q(
            member_subscription__subscription=subscription,
            member_subscription__active=True,
        )
        & url_filter
    ).select_related("member_subscription")

    if len(invoices) == 0:
        messages.error(request, _("No matching invoices found"))
        return HttpResponseRedirect(
            redirect_to=reverse_lazy(
                "dashboard", kwargs={"subscription_name": subscription.name}
            ),
        )
    generator = PDFGenerator()
    pdf_output = generator.generate_pdf([i for i in invoices.all()])
    return HttpResponse(pdf_output.read(), content_type="application/pdf")


@login_required
def pdfs_by_subscription_blank(request, subscription_id: int) -> HttpResponse:
    subscription = get_object_or_404(Subscription, pk=subscription_id)
    generator = PDFGenerator()
    pdf_output = generator.generate_pdf_blank(subscription)
    return HttpResponse(pdf_output.read(), content_type="application/pdf")


@login_required
def mark_created_as_pending_by_subscription(
    request, subscription_id: int
) -> HttpResponse:
    subscription = get_object_or_404(Subscription, pk=subscription_id)
    invoices = Invoice.objects.filter(
        member_subscription__subscription=subscription,
        member_subscription__active=True,
        status__in=[InvoiceStatusEnum.CREATED],
    )
    for invoice in invoices:
        invoice.status = InvoiceStatusEnum.PENDING
        invoice.save()
    return HttpResponseRedirect(
        redirect_to=reverse_lazy(
            "dashboard", kwargs={"subscription_name": subscription.name}
        ),
        content_type="application/pdf",
    )


@login_required
def create_reminder(request, invoice_id: int) -> HttpResponse:
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    if invoice.can_create_reminder():
        invoice.create_reminder()

    return HttpResponseRedirect(
        redirect_to=reverse_lazy(
            "dashboard",
            kwargs={"subscription_name": invoice.member_subscription.subscription.name},
        ),
        content_type="application/pdf",
    )


@login_required
def create_reminder_for_pending_by_subscription(
    request, subscription_id: int
) -> HttpResponse:
    subscription = get_object_or_404(Subscription, pk=subscription_id)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    invoices = Invoice.objects.filter(
        member_subscription__subscription=subscription,
        member_subscription__active=True,
        status__in=[InvoiceStatusEnum.PENDING],
        updated_at__lt=thirty_days_ago,
    )
    for invoice in invoices:
        invoice.create_reminder()
    return HttpResponseRedirect(
        redirect_to=reverse_lazy(
            "dashboard", kwargs={"subscription_name": subscription.name}
        ),
        content_type="application/pdf",
    )


@login_required
def create_first_invoices_by_subscription(
    request, subscription_id: int
) -> HttpResponse:
    subscription = get_object_or_404(Subscription, pk=subscription_id)
    member_subscriptions = MemberSubscription.objects.annotate(
        nb_invoices=Count("invoices")
    ).filter(subscription=subscription, parent=None, active=True, nb_invoices=0)

    if len(member_subscriptions) == 0:
        messages.error(request, _("No matching subscription found"))
        return HttpResponseRedirect(
            redirect_to=reverse_lazy(
                "dashboard", kwargs={"subscription_name": subscription.name}
            ),
        )

    for member_subscription in member_subscriptions:
        member_subscription.generate_new_invoice()
    return HttpResponseRedirect(
        redirect_to=reverse_lazy(
            "dashboard", kwargs={"subscription_name": subscription.name}
        ),
        content_type="application/pdf",
    )


@login_required
def create_missing_invoice_by_member_subscription(
    request, member_subscription_id: int
) -> HttpResponse:
    member_subscription = get_object_or_404(
        MemberSubscription, pk=member_subscription_id
    )

    if member_subscription.should_create_new_invoice():
        member_subscription.generate_new_invoice()

    return HttpResponseRedirect(
        reverse_lazy(
            "dashboard",
            kwargs={"subscription_name": member_subscription.subscription.name},
        )
    )
