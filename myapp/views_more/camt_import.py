from django.core.files.base import ContentFile
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.middleware.csrf import get_token
from ..models import Subscription, Invoice, InvoiceStatusEnum, MemberSubscription
from ..settings import FILE_UPLOAD_MAX_MEMORY_SIZE
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.urls import reverse_lazy
from django import forms
from django.core.files.storage import default_storage
from django.views.generic.edit import FormView
from ..camt_importer.camt_importer import CamtImporter

SESSION_FILENAME = "camt_import"
SESSION_SUBSCRIPTION_ID = "camt_import_subscription_pk"


class CamtUploadForm(forms.Form):
    camt_file = forms.FileField(
        label="Select a CAMT file", help_text=_("File must be in CAMT format")
    )

    subscription_widget = forms.widgets.Select(
        attrs={"class": "text-sm rounded-lg block w-full p-2.5"}
    )

    subscription = forms.ModelChoiceField(
        queryset=Subscription.objects,
        widget=subscription_widget,
        help_text=_("Select a subscription"),
    )


class CamtUploadView(FormView, TemplateView):
    form_class = CamtUploadForm
    success_url = reverse_lazy("camt_process")
    template_name = "myapp/camt_upload.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["data"] = []
        if SESSION_FILENAME in self.request.session:
            file_name = (
                self.request.session[SESSION_FILENAME]
                if SESSION_FILENAME in self.request.session
                else None
            )
            context["file_name"] = (
                file_name if default_storage.exists(file_name) else None
            )
        return context

    def form_valid(self, form):
        camt_file = form.cleaned_data["camt_file"]
        subscription = form.cleaned_data["subscription"]

        if not camt_file.name.lower().endswith(".xml"):
            messages.error(self.request, _("Please upload a XML file"))
            return super().form_invalid(form)

        if camt_file.size > FILE_UPLOAD_MAX_MEMORY_SIZE:
            messages.error(self.request, _("File too large"))
            return super().form_invalid(form)

        # Delete previously uploaded file
        if SESSION_FILENAME in self.request.session:
            default_storage.delete(self.request.session[SESSION_FILENAME])
            del self.request.session[SESSION_FILENAME]

        try:
            file = camt_file.read()
            if file is None:
                messages.error(self.request, _("Please upload a valid CSV file"))
            # Save the file
            file_path = default_storage.save(
                f"uploads/{camt_file.name}", ContentFile(file)
            )
            self.request.session[SESSION_FILENAME] = file_path
            self.request.session[SESSION_SUBSCRIPTION_ID] = subscription.pk

            CamtImporter(default_storage.open(file_path))

            messages.success(self.request, _("CAMT file uploaded successfully!"))
        except Exception as e:
            messages.error(self.request, str(_("Error processing file: %s")) % str(e))
            return super().form_invalid(form)

        return super().form_valid(form)


class CamtLinkInvoice(TemplateView):
    template_name = "myapp/partials/camt_link.html"
    invoice_id = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data()

        invoice = get_object_or_404(
            Invoice, pk=self.invoice_id if self.invoice_id else 0
        )
        context["invoice"] = invoice

        return context

    def get(self, request, *args, **kwargs):
        self.invoice_id = kwargs.get("invoice_id")
        transaction_id = kwargs.get("transaction_id")
        amount = kwargs.get("amount")

        context = self.get_context_data(**kwargs)
        invoice = context["invoice"]

        price = int(float(amount) * 100)

        if invoice.should_split(price, transaction_id):
            invoice.split_and_pay(price, transaction_id)
        else:
            invoice.transaction_id = transaction_id
            invoice.status = InvoiceStatusEnum.PAID
            invoice.price = price
            invoice.save()

        return self.render_to_response(context)


class CamtReconciliationView(TemplateView):
    route = "camt_reconciliation"
    template_name = "myapp/partials/camt_reconciliation.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["csrf_token"] = get_token(self.request)

        if self.request.method == "GET":
            context.update(
                {
                    "invoices": self._invoices(),
                    "member_subscriptions": MemberSubscription.objects.filter(
                        subscription_id=self.request.session[SESSION_SUBSCRIPTION_ID],
                        active=True,
                    ).all(),
                    "invoice_id": self.request.GET.get("invoice_id"),
                    "amount": self.request.GET.get("amount"),
                    "transaction_id": self.request.GET.get("transaction_id"),
                    "label": self.request.GET.get("label"),
                }
            )

        if self.request.method == "POST":
            context.update(
                {
                    "new_invoice_for_subscription": self.request.POST.get(
                        "new_invoice_for_subscription"
                    )
                    if self.request.POST.get("new_invoice_for_subscription")
                    else None,
                    "invoice_id": self.request.POST.get("invoice_id")
                    if self.request.POST.get("invoice_id")
                    else None,
                    "transaction_id": self.request.POST.get("transaction_id"),
                    "amount": self.request.POST.get("amount"),
                }
            )

        return context

    def _invoices(self):
        return (
            Invoice.objects.filter(
                member_subscription__subscription_id=self.request.session[
                    SESSION_SUBSCRIPTION_ID
                ],
                member_subscription__active=True,
            )
            .order_by(
                "created_at", "reminder", "status", "member_subscription__member_id"
            )
            .all()
        )

    def post(self, request, *args, **kwargs) -> HttpResponse:
        context = self.get_context_data(**kwargs)
        if context["invoice_id"] is not None:
            return self.add_invoice(context)

        if context["new_invoice_for_subscription"] is not None:
            return self.new_invoice_for_subscription(context)

        return HttpResponse("Error")

    def get(self, request, *args, **kwargs) -> HttpResponse:
        return super().get(request, *args, **kwargs)

    @staticmethod
    def add_invoice(context: dict) -> HttpResponse:
        invoice = (
            Invoice.objects.get(pk=context["invoice_id"])
            if context["invoice_id"]
            else None
        )

        if (
            invoice is not None
            and context["transaction_id"] is not None
            and context["transaction_id"] != ""
        ):
            price = int(float(context["amount"]) * 100)

            if invoice.should_split(price, context["transaction_id"]):
                invoice.split_and_pay(price, context["transaction_id"])
                response = _("Invoice split and paid successfully")
            else:
                invoice.transaction_id = context["transaction_id"]
                invoice.price = price
                invoice.status = InvoiceStatusEnum.PAID
                invoice.save()
                response = _("Invoice paid")

            return HttpResponse(response)
        return HttpResponse(_("Error while processing reconcilation"))

    @staticmethod
    def new_invoice_for_subscription(context: dict) -> HttpResponse:
        member_subscription = get_object_or_404(
            MemberSubscription, pk=context["new_invoice_for_subscription"]
        )
        invoice = member_subscription.generate_new_invoice()
        price = int(float(context["amount"]) * 100)
        invoice.price = price
        invoice.status = InvoiceStatusEnum.PAID
        invoice.save()
        return HttpResponse(_("New invoice created"))


class CamtProcessView(TemplateView):
    template_name = "myapp/camt_process.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        file = default_storage.open(self.request.session[SESSION_FILENAME])

        subscription = (
            self.request.session[SESSION_SUBSCRIPTION_ID]
            if SESSION_SUBSCRIPTION_ID in self.request.session
            else None
        )
        subscription = (
            Subscription.objects.get(pk=subscription) if subscription else None
        )

        context["subscription"] = subscription
        context["data"] = CamtImporter(file).transactions()

        return context

    def get(self, request, *args, **kwargs):
        if SESSION_FILENAME not in self.request.session or not default_storage.exists(
            self.request.session[SESSION_FILENAME]
        ):
            return HttpResponseRedirect(redirect_to=reverse_lazy("camt_upload"))

        return super().get(request, *args, **kwargs)
