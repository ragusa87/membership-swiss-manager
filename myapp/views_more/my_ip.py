from django.http import HttpResponse, HttpRequest


def my_ip(request: HttpRequest) -> HttpResponse:
    mylist = {
        "forwarded": request.headers.get("X-Forwarded-For"),
        "remote_addr": request.META.get("REMOTE_ADDR"),
    }

    return HttpResponse(str(mylist), content_type="text/plain")
