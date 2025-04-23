"""
URL configuration for myapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, re_path
from . import views
from django.views.generic.base import RedirectView

from .views_more.assign import AssignUserFormView
from .views_more.invoices import (
    pdf_by_invoice,
    pdfs_by_subscription,
    create_reminder_for_pending_by_subscription,
    mark_created_as_pending_by_subscription,
    create_first_invoices_by_subscription,
    pdfs_by_subscription_blank,
)
from .views_more.dashboard import DashboardView
from .views_more.switch_language import switch_language
from .views_more.my_ip import my_ip
from .views_more.export_subscription import export_subscription
from .settings import DEBUG
from debug_toolbar.toolbar import debug_toolbar_urls
from .views_more.csv_upload import CSVUploadView, CsvImport
from .views_more.camt_import import (
    CamtUploadView,
    CamtProcessView,
    CamtReconciliationView,
    CamtLinkInvoice,
)

favicon_view = RedirectView.as_view(url="/assets/favicon.ico", permanent=True)
urlpatterns = [
    path("admin/", admin.site.urls),
    path("ip/", my_ip),
    path("", views.index, name="index"),
    path("dashboard/", views.index, name="index_dashboards"),
    path("import-camt", CamtUploadView.as_view(), name="camt_upload"),
    path("process-camt", CamtProcessView.as_view(), name="camt_process"),
    path(
        "dashboard/<str:subscription_name>", DashboardView.as_view(), name="dashboard"
    ),
    path(
        "assign/<str:subscription_name>",
        AssignUserFormView.as_view(),
        name="assign_user",
    ),
    path("invoice/<int:invoice_id>/pdf/", pdf_by_invoice, name="pdf_by_invoice"),
    path(
        "invoices/<int:subscription_id>/pdf/",
        pdfs_by_subscription,
        name="pdf_by_subscription",
    ),
    path(
        "invoices/<int:subscription_id>/pdf-blank/",
        pdfs_by_subscription_blank,
        name="pdf_by_subscription_blank",
    ),
    path(
        "process-camt_reconciliation",
        CamtReconciliationView.as_view(),
        name="camt_reconciliation",
    ),
    re_path(
        r"^camt_link/(?P<invoice_id>\d+)/(?P<amount>[^/]+)/(?P<transaction_id>.+)/$",
        CamtLinkInvoice.as_view(),
        name="camt_link",
    ),
    path(
        "invoices/<int:subscription_id>/create_reminder_for_pending/",
        create_reminder_for_pending_by_subscription,
        name="create_reminder_for_pending_by_subscription",
    ),
    path(
        "invoices/<int:subscription_id>/mark_created_as_pending/",
        mark_created_as_pending_by_subscription,
        name="mark_created_as_pending_by_subscription",
    ),
    path(
        "invoices/<int:subscription_id>/create_first_invoices_by_subscription/",
        create_first_invoices_by_subscription,
        name="create_first_invoices_by_subscription",
    ),
    re_path(r"^favicon\.ico$", favicon_view),
    path("switch_language", switch_language, name="switch_language"),
    path("import-csv/1", CSVUploadView.as_view(), name="csv_import"),
    path("import-csv/<int:step>", CsvImport.as_view(), name="csv_import_step"),
    path(
        "export-subscriptions/<str:subscription_name>.<str:extension>",
        export_subscription,
        name="subscription_export_with_extension",
    ),
    path(
        "export-subscriptions/<str:subscription_name>.xlsx",
        export_subscription,
        {"extension": "xlsx"},
        name="subscription_export",
    ),
]

if DEBUG:
    urlpatterns += debug_toolbar_urls()
