from ..settings import LANGUAGES
from django.utils import translation
from django.http import HttpResponseRedirect


def switch_language(request):
    """
    View to change the language.
    POST `language` should be a language code like 'en', 'es', 'fr', etc.
    """
    next_url = request.META.get("HTTP_REFERER", "/")  # Go back to the referring page
    response = HttpResponseRedirect(next_url)
    lang_code = request.POST.get("language", request.GET.get("language"))
    if lang_code in dict(LANGUAGES):  # Check if the lang_code is valid
        translation.activate(lang_code)
        request.session["django_language"] = lang_code
        response.set_cookie("django_language", lang_code)

    return response
