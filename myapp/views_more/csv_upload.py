from django.core.files.base import ContentFile
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView

from ..cvs_manager.csv_importer import CsvImporter
from ..models import Subscription
from ..settings import FILE_UPLOAD_MAX_MEMORY_SIZE
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django import forms
from django.core.files.storage import default_storage


SESSION_FILENAME = "csv_upload_file"
SESSION_SUBSCRIPTION_ID = "csv_subscription_id"


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Select a CSV file", help_text=_("File must be in CSV format")
    )

    subscription_widget = forms.widgets.Select(
        attrs={"class": "text-sm rounded-lg block w-full p-2.5"}
    )

    subscription = forms.ModelChoiceField(
        queryset=Subscription.objects,
        widget=subscription_widget,
        help_text=_("Select a subscription"),
    )


class CSVUploadView(FormView):
    template_name_model = "myapp/upload_csv_step_%d.html"
    form_class = CSVUploadForm
    step = 1

    success_url = reverse_lazy("csv_import_step", kwargs={"step": 2})

    def post(self, request, *args, **kwargs):
        self.step = self.kwargs["step"] if "step" in self.kwargs else 1
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.step = self.kwargs["step"] if "step" in self.kwargs else 1

        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["step"] = self.step

        if self.step == 2:
            file_name = (
                self.request.session[SESSION_FILENAME]
                if "csv_file" in self.request.session
                else None
            )
            context["file_name"] = (
                file_name if default_storage.exists(file_name) else None
            )

        return context

    def render_to_response(self, context, **response_kwargs):
        step = int(context["step"]) if "step" in context else 1
        self.template_name = self.template_name_model % step
        self.success_url = reverse_lazy("csv_import_step", kwargs={"step": step + 1})
        return super().render_to_response(context, **response_kwargs)

    def form_valid(self, form):
        csv_file = form.cleaned_data["csv_file"]

        if not csv_file.name.endswith(".csv"):
            messages.error(self.request, _("Please upload a CSV file"))
            return super().form_invalid(form)

        if csv_file.size > FILE_UPLOAD_MAX_MEMORY_SIZE:
            messages.error(self.request, _("File too large"))
            return super().form_invalid(form)

        # Delete previously uploaded file
        if SESSION_FILENAME in self.request.session:
            default_storage.delete(self.request.session[SESSION_FILENAME])

        try:
            file = csv_file.read()
            if file is None:
                messages.error(self.request, _("Please upload a valid CSV file"))
            # Save the file
            file_path = default_storage.save(
                f"uploads/{csv_file.name}", ContentFile(file)
            )
            self.request.session[SESSION_FILENAME] = file_path
            self.request.session[SESSION_SUBSCRIPTION_ID] = form.data["subscription"]

            messages.success(self.request, _("CSV file uploaded successfully!"))
        except Exception as e:
            messages.error(self.request, _("Error processing file: %s") % str(e))
            return super().form_invalid(form)

        return super().form_valid(form)


class CsvImport(TemplateView):
    step = 2
    template_name = "myapp/upload_csv_step_%d.html" % step

    def __session_valid__(self) -> bool:
        if (
            SESSION_FILENAME not in self.request.session
            or SESSION_SUBSCRIPTION_ID not in self.request.session
        ):
            return False
        if not default_storage.exists(self.request.session[SESSION_FILENAME]):
            return False
        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        subscription = Subscription.objects.get(
            pk=int(self.request.session[SESSION_SUBSCRIPTION_ID])
        )
        context["subscription"] = subscription

        importer = CsvImporter(subscription)

        context["data"] = []
        path = default_storage.path(str(self.request.session[SESSION_FILENAME]))
        with open(path, "r", encoding="utf-8") as file:
            context["data"] = importer.do_import(file)

        return context

    def get(self, request, *args, **kwargs):
        self.step = self.kwargs["step"] if "step" in self.kwargs else 2

        if not self.__session_valid__():
            messages.error(self.request, _("Session expired, try again"))
            return HttpResponseRedirect(
                redirect_to=reverse_lazy("csv_import_step", kwargs={"step": 1})
            )
        try:
            return super().get(request, *args, **kwargs)
        except RuntimeError as e:
            messages.error(self.request, _("Error processing file: %s") % str(e))
            return HttpResponseRedirect(
                redirect_to=reverse_lazy("csv_import_step", kwargs={"step": 1})
            )
