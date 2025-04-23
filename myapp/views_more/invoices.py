from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from myapp.models import Invoice, Subscription, InvoiceStatusEnum, MemberSubscription
from myapp.pdf_generator import PDFGenerator
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


def pdf_by_invoice(self, invoice_id: int) -> HttpResponse:
    generator = PDFGenerator()
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    pdf_output = generator.generate_pdf([invoice])
    return HttpResponse(pdf_output.read(), content_type="application/pdf")


def pdfs_by_subscription(self, subscription_id: int) -> HttpResponse:
    subscription = get_object_or_404(Subscription, pk=subscription_id)
    invoices = Invoice.objects.filter(
        member_subscription__subscription=subscription,
        member_subscription__active=True,
        status__in=[InvoiceStatusEnum.CREATED],
    )

    if len(invoices) == 0:
        messages.error(self, _("No matching invoices found"))
        return HttpResponseRedirect(
            redirect_to=reverse_lazy(
                "dashboard", kwargs={"subscription_name": subscription.name}
            ),
        )
    generator = PDFGenerator()
    pdf_output = generator.generate_pdf([i for i in invoices.all()])
    return HttpResponse(pdf_output.read(), content_type="application/pdf")


def pdfs_by_subscription_blank(request, subscription_id: int) -> HttpResponse:
    subscription = get_object_or_404(Subscription, pk=subscription_id)
    generator = PDFGenerator()
    pdf_output = generator.generate_pdf_blank(subscription)
    return HttpResponse(pdf_output.read(), content_type="application/pdf")


def mark_created_as_pending_by_subscription(self, subscription_id: int) -> HttpResponse:
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


def create_reminder_for_pending_by_subscription(
    self, subscription_id: int
) -> HttpResponse:
    subscription = get_object_or_404(Subscription, pk=subscription_id)
    invoices = Invoice.objects.filter(
        member_subscription__subscription=subscription,
        member_subscription__active=True,
        status__in=[InvoiceStatusEnum.PENDING],
    )
    for invoice in invoices:
        invoice.create_reminder()
    return HttpResponseRedirect(
        redirect_to=reverse_lazy(
            "dashboard", kwargs={"subscription_name": subscription.name}
        ),
        content_type="application/pdf",
    )


def create_first_invoices_by_subscription(self, subscription_id: int) -> HttpResponse:
    subscription = get_object_or_404(Subscription, pk=subscription_id)
    member_subscriptions = MemberSubscription.objects.annotate(
        nb_invoices=Count("invoices")
    ).filter(subscription=subscription, parent=None, active=True, nb_invoices=0)

    if len(member_subscriptions) == 0:
        messages.error(self, _("No matching subscription found"))
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
