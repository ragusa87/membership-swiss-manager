from django.core.files.base import ContentFile
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from django.forms.utils import RenderableMixin

from ..models import Subscription
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

        if (
            SESSION_FILENAME in self.request.session
            and default_storage.exists(self.request.session[SESSION_FILENAME])
            and SESSION_SUBSCRIPTION_ID in self.request.session
        ):
            return HttpResponseRedirect(redirect_to=reverse_lazy("camt_process"))

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
