from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from myapp.models import Invoice
from myapp.pdf_generator import PDFGenerator


def index(request):
    return HttpResponse("Hello, world.")


def single_invoice(self, invoice_id: int) -> HttpResponse:
    generator = PDFGenerator()
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    pdf_output = generator.generate_pdf([invoice])
    return HttpResponse(pdf_output.read(), content_type="application/pdf")
