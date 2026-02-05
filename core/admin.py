from django import forms
from django.db.models.aggregates import Count
from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from core.models.member import Member
from core.models.member_subscription import MemberSubscription
from core.models.invoice import Invoice, InvoiceStatusEnum
from core.models.subscription import Subscription
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Prefetch
from core.templatetags.custom_filters import format_price
from .forms.invoice import InvoiceForm
from .forms.subscription import SubscriptionForm
from .pdf_generator.pdf_generator import PDFGenerator


class FilterMemberSubscriptionBySubscription(SimpleListFilter):
    title = "subscription"
    parameter_name = "subscription"

    def lookups(self, request, model_admin):
        return [
            (subscription.pk, subscription.name)
            for subscription in Subscription.objects.all()
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(subscription__pk=self.value())
        return queryset


class FilterMemberSubscriptionByMember(SimpleListFilter):
    title = "member"
    parameter_name = "member"

    def lookups(self, request, model_admin):
        members = (
            Member.objects.all()
        )  # You can filter which parents you want to show here
        return [(member.pk, f"{member.get_fullname()}") for member in members]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(member__id=self.value())
        return queryset


class FilterInvoiceByStatus(SimpleListFilter):
    title = "status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return [(status, label) for status, label in InvoiceStatusEnum.choices]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class FilterInvoiceBySubscription(SimpleListFilter):
    title = "subscription"
    parameter_name = "subscription"

    def lookups(self, request, model_admin):
        return [
            (subscription.pk, subscription.name)
            for subscription in Subscription.objects.all()
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(member_subscription__subscription=self.value())
        return queryset


class FilterInvoiceByMemberSubscription(SimpleListFilter):
    title = "member subscription"
    parameter_name = "member_subscription"

    def lookups(self, request, model_admin):
        return [
            (subscription.pk, str(subscription))
            for subscription in MemberSubscription.objects.all()
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(member_subscription=self.value())
        return queryset


class FilterById(SimpleListFilter):
    title = _("Filter by Id")
    parameter_name = "id"

    def lookups(self, request, model_admin):
        return []

    def has_output(self):
        return True

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(pk=self.value())
        return queryset


class MemberAdmin(admin.ModelAdmin):
    title = "Member"
    list_filter = [FilterById]
    search_fields = ["firstname", "lastname", "email", "address", "phone"]

    def get_list_display(self, request):
        default_list_display = super().get_list_display(request)
        return default_list_display + (
            "email",
            "phone",
            "full_address",
            "view_subscriptions",
        )

    def full_address(self, obj):
        address = [obj.address, obj.address_number, obj.zip, obj.city]
        address = [str(i) for i in address if str(i if i else "").strip() != ""]
        if address:
            return format_html(" ".join(address))
        return ""

    def view_subscriptions(self, obj):
        name = "View subscriptions"
        url = (
            reverse("admin:core_membersubscription_changelist")
            + "?member="
            + str(obj.pk)
        )
        return format_html('<a href="{}">{}</a>', url, name)


class SubscriptionAdmin(admin.ModelAdmin):
    form = SubscriptionForm
    list_display = ("name", "view_dashboard")

    def view_dashboard(self, obj):
        url = reverse("dashboard", kwargs={"subscription_name": obj.name})
        return format_html('<a href="{}">View dashboard</a>', url)

    view_dashboard.short_description = "Dashboard"


@admin.action(description="Export the selected invoices as PDF")
def export_invoices_pdf(modeladmin, request, queryset):
    generator = PDFGenerator()
    pdf_output = generator.generate_pdf(queryset.all())

    return HttpResponse(pdf_output.read(), content_type="application/pdf")


@admin.action(description="Mark as canceled")
def mark_as_canceled(modeladmin, request, queryset):
    invoices = queryset.all()
    for invoice in invoices:
        invoice.status = InvoiceStatusEnum.CANCELED
        invoice.save()


@admin.action(description="Create reminder")
def create_reminder(modeladmin, request, queryset):
    invoices = queryset.all()
    for invoice in invoices:
        invoice.create_reminder()


@admin.action(description="Mark as pending")
def mark_as_pending(modeladmin, request, queryset):
    invoices = queryset.all()
    for invoice in invoices:
        invoice.status = InvoiceStatusEnum.PENDING
        invoice.save()


@admin.action(description="Mark as paid")
def mark_as_paid(modeladmin, request, queryset):
    invoices = queryset.all()
    for invoice in invoices:
        invoice.status = InvoiceStatusEnum.PAID
        invoice.save()


class InvoiceAdmin(admin.ModelAdmin):
    form = InvoiceForm
    list_filter = [
        FilterInvoiceByStatus,
        FilterInvoiceBySubscription,
        FilterInvoiceByMemberSubscription,
        FilterById,
    ]
    actions = [
        export_invoices_pdf,
        mark_as_canceled,
        create_reminder,
        mark_as_pending,
        mark_as_paid,
    ]
    ordering = ["-created_at"]

    def get_list_display(self, request):
        default_list_display = super().get_list_display(request)
        return default_list_display + (
            "view_status",
            "view_price",
            "view_member",
            "view_subscription",
            "view_created_at",
            "view_reminder",
            "view_pdf",
        )

    def view_member(self, obj):
        name = obj.member_subscription.member.get_shortname()
        url = (
            reverse("admin:core_member_changelist")
            + "?id="
            + str(obj.member_subscription.member.pk)
        )
        return format_html('<a href="{}">{}</a>', url, name)

    def view_subscription(self, obj):
        return format_html(obj.member_subscription.subscription.name)

    def view_status(self, obj):
        return format_html(obj.get_status_text())

    def view_price(self, obj):
        return format_html(format_price(obj.price))

    def view_reminder(self, obj):
        return format_html(obj.get_reminder_text())

    def view_created_at(self, obj):
        name = obj.created_at.strftime("%Y-%m-%d")
        return format_html("{}", name)

    def view_pdf(self, obj):
        url = reverse("pdf_by_invoice", kwargs={"invoice_id": obj.pk})
        return format_html(
            '<a href="{}" target="_blank" class="button default">View PDF</a>', url
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("member_subscription").prefetch_related(
            Prefetch(
                "member_subscription",
                queryset=MemberSubscription.objects.select_related(
                    "member"
                ).select_related("subscription"),
            )
        )

    view_pdf.short_description = "PDF"
    view_member.short_description = "Member"
    view_subscription.short_description = "Subscription"
    view_created_at.short_description = "Created at"
    view_price.short_description = "Price"
    view_reminder.short_description = "Reminder"


class MemberSubscriptionForm(forms.ModelForm):
    class Meta:
        model = MemberSubscription
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        parent = cleaned_data.get("parent")
        subscription = cleaned_data.get("subscription")

        # Check if parent and subscription are aligned
        if parent and subscription:
            if parent.subscription != subscription:
                raise forms.ValidationError(
                    "The parent and subscription fields must be aligned."
                )

        return cleaned_data


class MemberSubscriptionAdmin(admin.ModelAdmin):
    form = MemberSubscriptionForm

    list_filter = (
        FilterMemberSubscriptionBySubscription,
        FilterMemberSubscriptionByMember,
        FilterById,
    )
    readonly_fields = ["price"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            object_id = request.resolver_match.kwargs.get("object_id")
            if object_id:
                obj = self.get_object(request, object_id)
                if obj and obj.subscription:
                    kwargs["queryset"] = MemberSubscription.objects.filter(
                        parent=None, subscription=obj.subscription
                    )  # Adjust the filter

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_list_display(self, request):
        default_list_display = super().get_list_display(request)
        return default_list_display + (
            "view_member",
            "parent",
            "active",
            "view_invoices",
        )

    def view_member(self, obj):
        name = obj.member.get_fullname()
        url = reverse("admin:core_member_changelist") + "?id=" + str(obj.member.pk)
        return format_html('<a href="{}">{}</a>', url, name)

    def view_invoices(self, obj):
        name = "invoices (%s)" % (str(obj.invoices_count) if obj.invoices_count else 0)
        url = (
            reverse("admin:core_invoice_changelist")
            + "?member_subscription="
            + str(obj.pk)
        )
        return format_html('<a href="{}">{}</a>', url, name)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(invoices_count=Count("invoices"))

    view_member.short_description = "Member"
    view_invoices.short_description = "Invoices"


admin.site.register(Member, MemberAdmin)
admin.site.register(MemberSubscription, MemberSubscriptionAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Invoice, InvoiceAdmin)
