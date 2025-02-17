from django.core.files.base import ContentFile
from django.forms.utils import RenderableMixin
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView

from ..cvs_manager.csv_importer import CsvImporter, Export
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


class StepAwareMixin(RenderableMixin):
    step = 1
    max_step = 4
    steps = [_("step.upload_csv"), _("step.create_members"), _("step.import")]
    template_name_model = "myapp/upload_csv_step_%d.html"


class CSVUploadForm(StepAwareMixin, forms.Form):
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


class CSVUploadView(StepAwareMixin, FormView):
    template_name_model = "myapp/upload_csv_step_%d.html"
    form_class = CSVUploadForm
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
        context["steps"] = self.steps
        context["step_name"] = (
            self.steps[self.step - 1]
            if self.step - 1 < len(self.steps) and self.step > 0
            else None
        )
        context["is_last_step"] = False

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
        self.success_url = reverse_lazy(
            "csv_import_step", kwargs={"step": self.step + 1}
        )
        self.template_name = self.template_name_model % self.step
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


class CsvImport(TemplateView, StepAwareMixin):
    step = 2

    def __session_valid__(self) -> bool:
        if (
            SESSION_FILENAME not in self.request.session
            or SESSION_SUBSCRIPTION_ID not in self.request.session
        ):
            return False
        if not default_storage.exists(self.request.session[SESSION_FILENAME]):
            return False
        return True

    def get_subscription(self) -> Subscription | None:
        if SESSION_SUBSCRIPTION_ID not in self.request.session:
            return None

        return Subscription.objects.get(
            pk=int(self.request.session[SESSION_SUBSCRIPTION_ID])
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subscription = self.get_subscription()
        context["subscription"] = subscription
        context["previous_step"] = self.step - 1 if self.step > 1 else None
        importer = CsvImporter(subscription)
        context["step"] = self.step
        context["steps"] = self.steps
        context["step_name"] = (
            self.steps[self.step - 1]
            if self.step - 1 < len(self.steps) and self.step > 0
            else None
        )
        context["is_last_step"] = self.step >= self.max_step

        context["data"] = None
        path = default_storage.path(str(self.request.session[SESSION_FILENAME]))
        with open(path, "r", encoding="utf-8") as file:
            context["data"] = importer.do_import(subscription, file)

        return context

    def do_import(self):
        context = self.get_context_data()
        export: Export = context["data"]

        if export.has_missing_users():
            raise RuntimeError("Missing users")

        if export.has_existing_member_subscriptions():
            raise RuntimeError("This subscription is not empty")

        for row in export.rows:
            subscription = row.as_member_subscription()
            subscription.save()
            children = row.as_child_subscriptions(subscription)
            for child in children:
                child.save()

    def get(self, request, *args, **kwargs):
        self.step = self.kwargs["step"] if "step" in self.kwargs else 1
        self.template_name = self.template_name_model % self.step

        if not self.__session_valid__():
            messages.error(self.request, _("Session expired, try again"))
            return HttpResponseRedirect(
                redirect_to=reverse_lazy("csv_import_step", kwargs={"step": 1})
            )
        try:
            if self.step == self.max_step:
                self.template_name = self.template_name_model % (self.max_step - 1)

                subscription = Subscription.objects.get(
                    pk=int(self.request.session[SESSION_SUBSCRIPTION_ID])
                )

                self.do_import()

                return HttpResponseRedirect(
                    redirect_to=reverse_lazy(
                        "dashboard", kwargs={"subscription_name": subscription.name}
                    )
                )

            return super().get(request, *args, **kwargs)
        except RuntimeError as e:
            messages.error(self.request, _("Error processing file: %s") % str(e))
            return HttpResponseRedirect(
                redirect_to=reverse_lazy("csv_import_step", kwargs={"step": 1})
            )
