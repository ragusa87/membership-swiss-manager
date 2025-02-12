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
from .views import single_invoice, DashboardView, switch_language, my_ip
from .settings import DEBUG
from debug_toolbar.toolbar import debug_toolbar_urls

favicon_view = RedirectView.as_view(url="/assets/favicon.ico", permanent=True)
urlpatterns = [
    path("admin/", admin.site.urls),
    path("ip/", my_ip),
    path("", views.index, name="index"),
    path(
        "dashboard/<str:subscription_name>", DashboardView.as_view(), name="dashboard"
    ),
    path("invoice/<int:invoice_id>/pdf/", single_invoice, name="single_invoice_pdf"),
    re_path(r"^favicon\.ico$", favicon_view),
    path("switch_language", switch_language, name="switch_language"),
]

if DEBUG:
    urlpatterns += debug_toolbar_urls()
