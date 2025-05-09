from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.views.generic.edit import FormView
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

from myapp.forms.subscription_user_form import MemberSubscriptionUserForm, MemberForm
from myapp.models import Subscription, MemberSubscription, Member


class AssignUserFormView(FormView, LoginRequiredMixin):
    template_name = "myapp/assign_user.html"
    form_class = MemberForm

    def dispatch(self, request, *args, **kwargs):
        self.subscription = get_object_or_404(
            Subscription, name=self.kwargs["subscription_name"]
        )
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.POST.get("form") == "link":
            for form in self._get_forms():
                if form.is_bound and form.is_valid():
                    form.instance.subscription = self.subscription
                    form.save()
            return HttpResponseRedirect(self.get_success_url())
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        form.save(commit=True)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "assign_user", kwargs={"subscription_name": self.subscription.name}
        )

    def _get_candidates(self):
        assigned_users_ids = MemberSubscription.objects.filter(
            subscription=self.subscription
        ).values_list("member__pk", flat=True)
        assigned_children = MemberSubscription.objects.filter(
            parent__in=MemberSubscription.objects.filter(
                subscription=self.subscription
            ),
        ).values_list("member__pk", flat=True)

        return (
            Member.objects.exclude(
                Q(pk__in=assigned_users_ids) | Q(pk__in=assigned_children)
            )
            .order_by("lastname", "firstname")
            .all()
        )

    def _get_forms(self, bound=True):
        return [
            MemberSubscriptionUserForm(
                data=self.request.POST if bound else None,
                prefix="link_member_%s" % m.pk,
                initial={"subscription": self.subscription, "member": m},
                instance=MemberSubscription(subscription=self.subscription, member=m),
            )
            for m in self._get_candidates()
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subscription"] = self.subscription
        context["forms"] = self._get_forms(bound=False)

        context["member_subscriptions"] = (
            MemberSubscription.objects.filter(
                subscription=self.subscription, parent__isnull=True
            )
            .order_by("member__firstname", "member__lastname")
            .prefetch_related("children")
            .select_related("parent", "member")
        )
        return context
