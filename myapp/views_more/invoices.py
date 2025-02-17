from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from myapp.models import Invoice, Subscription, InvoiceStatusEnum
from myapp.pdf_generator import PDFGenerator


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

    generator = PDFGenerator()
    pdf_output = generator.generate_pdf([i for i in invoices.all()])
    return HttpResponse(pdf_output.read(), content_type="application/pdf")
