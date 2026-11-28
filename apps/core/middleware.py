import sys
from django.conf import settings
from django.shortcuts import render


class SiteUnavailableMiddleware:
    """
    Blocks all site routes with a 'Website Unavailable' pop-up screen
    when settings.SITE_UNAVAILABLE is True (skipped during automated tests).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            getattr(settings, 'SITE_UNAVAILABLE', False)
            and 'test' not in sys.argv
            and not request.path.startswith(settings.STATIC_URL)
        ):
            return render(request, 'core/site_unavailable.html', status=503)
        return self.get_response(request)
