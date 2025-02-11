from django.contrib import admin
from myapp.models import Member
from myapp.models import MemberSubscription
from myapp.models import Invoice, InvoiceStatusEnum
from myapp.models import Subscription
from django.utils import timezone
from django.contrib.admin import SimpleListFilter


class MemberAdmin(admin.ModelAdmin):
    pass


class SubscriptionAdmin(admin.ModelAdmin):
    pass


class MemberSubscriptionCurrentYearFilter(SimpleListFilter):
    title = "recent years"
    parameter_name = "year"

    def lookups(self, request, model_admin):
        current_year = timezone.now().year

        return [(i, f"Year {i}") for i in range(current_year - 2, current_year)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(subscription__name=self.value())
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


class InvoiceAdmin(admin.ModelAdmin):
    list_filter = [InvoiceByStatus]


class MemberSubscriptionAdmin(admin.ModelAdmin):
    list_filter = (MemberSubscriptionCurrentYearFilter, MemberSubscriptionByMember)


admin.site.register(Member, MemberAdmin)
admin.site.register(MemberSubscription, MemberSubscriptionAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Invoice, InvoiceAdmin)
