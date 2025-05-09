from myapp.models.subscription import Subscription
from django.http import HttpResponseRedirect
from django.urls import reverse

from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    last = Subscription.objects.order_by("-created_at").first()
    if last:
        return HttpResponseRedirect(
            redirect_to=reverse("dashboard", kwargs={"subscription_name": last.name})
        )
    return HttpResponseRedirect(redirect_to="/admin")
