from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from ..models import Subscription
from ..cvs_manager.csv_exporter import CsvExporter


def get_mime_type(file_extension: str) -> str:
    match file_extension.lower():
        case "xlsx":
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        case "csv":
            return "text/csv"
        case _:
            return "application/octet-stream"


def export_subscription(self, subscription_name: str, extension: str) -> HttpResponse:
    subscription = get_object_or_404(Subscription, name=subscription_name)
    exporter = CsvExporter(subscription)

    return HttpResponse(
        exporter.export(extension).read(), content_type=get_mime_type(extension)
    )
