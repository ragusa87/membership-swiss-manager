from django.contrib import admin
from myapp.models import Member
from myapp.models import MemberSubscription
from myapp.models import Invoice, InvoiceStatusEnum
from myapp.models import Subscription
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Prefetch
from myapp.templatetags.custom_filters import format_price


class MemberAdmin(admin.ModelAdmin):
    pass


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("name", "view_dashboard")

    def view_dashboard(self, obj):
        url = reverse("dashboard", kwargs={"subscription_name": obj.name})
        return format_html('<a href="{}">View dashboard</a>', url)

    view_dashboard.short_description = "Dashboard"


class MemberSubscriptionBySubscription(SimpleListFilter):
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


class FilterById(SimpleListFilter):
    title = "Filter by Id"
    parameter_name = "id"

    def lookups(self, request, model_admin):
        return []

    def has_output(self):
        return True

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(pk=self.value())
        return queryset


class MemberSubscriptionByMember(SimpleListFilter):
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


class InvoiceByStatus(SimpleListFilter):
    title = "status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return [(status, label) for status, label in InvoiceStatusEnum.choices]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class InvoiceBySubscription(SimpleListFilter):
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


class InvoiceAdmin(admin.ModelAdmin):
    list_filter = [InvoiceByStatus, InvoiceBySubscription]

    def get_list_display(self, request):
        default_list_display = super().get_list_display(request)
        return default_list_display + (
            "view_member",
            "view_price",
            "view_subscription",
            "view_pdf",
        )

    def view_member(self, obj):
        return format_html(obj.member_subscription.member.get_fullname())

    def view_subscription(self, obj):
        return format_html(obj.member_subscription.subscription.name)

    def view_price(self, obj):
        return format_html(format_price(obj.price))

    def view_pdf(self, obj):
        url = reverse("single_invoice_pdf", kwargs={"invoice_id": obj.pk})
        return format_html('<a href="{}">View PDF</a>', url)

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
    view_member.short_description = "member"
    view_subscription.short_description = "subscription"


class MemberSubscriptionAdmin(admin.ModelAdmin):
    list_filter = (
        MemberSubscriptionBySubscription,
        MemberSubscriptionByMember,
        FilterById,
    )
    readonly_fields = ["price"]


admin.site.register(Member, MemberAdmin)
admin.site.register(MemberSubscription, MemberSubscriptionAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Invoice, InvoiceAdmin)
