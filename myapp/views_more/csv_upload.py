from django.core.files.base import ContentFile
from ..settings import FILE_UPLOAD_MAX_MEMORY_SIZE

from django.contrib import messages
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django import forms
from django.core.files.storage import default_storage


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Select a CSV file", help_text="File must be in CSV format"
    )


class CSVUploadView(FormView):
    template_name_model = "myapp/upload_csv_step_%d.html"
    form_class = CSVUploadForm
    success_url = reverse_lazy(
        "csv_import", kwargs={"step": 2}
    )  # Redirect to same page after upload

    def render_to_response(self, context, **response_kwargs):
        step = int(context["step"]) if "step" in context else 1
        self.template_name = self.template_name_model % step

        return super().render_to_response(context, **response_kwargs)

    def form_valid(self, form):
        csv_file = form.cleaned_data["csv_file"]

        if not csv_file.name.endswith(".csv"):
            messages.error(self.request, "Please upload a CSV file")
            return super().form_invalid(form)

        if csv_file.size > FILE_UPLOAD_MAX_MEMORY_SIZE:
            messages.error(self.request, "File too large")
            return super().form_invalid(form)

        # Delete previously uploaded file
        if "csv_file" in self.request.session:
            default_storage.delete(self.request.session["csv_file"])

        try:
            # Read the CSV file
            csv_file.read().decode("utf-8")

            # Save the file
            file_path = default_storage.save(
                f"uploads/{csv_file.name}", ContentFile(csv_file.read())
            )
            self.request.session["csv_file"] = file_path

            messages.success(self.request, "CSV file uploaded successfully!")
        except Exception as e:
            messages.error(self.request, f"Error processing file: {str(e)}")
            return super().form_invalid(form)

        return super().form_valid(form)
