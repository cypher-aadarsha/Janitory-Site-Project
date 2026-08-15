"""
Custom security middleware for adding Content-Security-Policy header.
"""
import os
import mimetypes
from django.conf import settings
from django.http import FileResponse, Http404


class MediaServeMiddleware:
    """
    Serves uploaded media files in production (when DEBUG=False).

    Django's built-in static() URL helper only serves MEDIA files when
    DEBUG=True. In production this middleware intercepts requests to
    MEDIA_URL and returns the file from MEDIA_ROOT directly.

    NOTE: For high-traffic sites, prefer serving media via Nginx instead.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.media_url = getattr(settings, 'MEDIA_URL', '/media/')
        self.media_root = str(getattr(settings, 'MEDIA_ROOT', ''))

    def __call__(self, request):
        if request.path.startswith(self.media_url):
            # Strip the media URL prefix to get the relative file path
            relative_path = request.path[len(self.media_url):]
            file_path = os.path.join(self.media_root, relative_path)

            # Security: prevent directory traversal
            real_path = os.path.realpath(file_path)
            if not real_path.startswith(os.path.realpath(self.media_root)):
                raise Http404("File not found.")

            if os.path.isfile(real_path):
                content_type, _ = mimetypes.guess_type(real_path)
                return FileResponse(open(real_path, 'rb'), content_type=content_type or 'application/octet-stream')

            raise Http404("File not found.")

        return self.get_response(request)


class AttributionMiddleware:
    """
    Captures Google Ads / UTM attribution on the visitor's landing page and
    keeps it in the session until they convert.

    A paid visitor lands on something like /?gclid=abc123 but usually submits
    the form from /contact/, by which point the query string is long gone.
    Stashing it in the session on first sight is what makes it possible to
    say which ad click produced which lead.

    First-touch wins: once a gclid is recorded for the session it is not
    overwritten, so a later organic page view cannot erase paid attribution.
    """

    TRACKED_PARAMS = ('gclid', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_term')
    SESSION_KEY = 'attribution'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only inspect normal page loads; skip media, static and admin noise.
        if request.method == 'GET' and hasattr(request, 'session'):
            captured = {
                param: request.GET[param][:500]
                for param in self.TRACKED_PARAMS
                if request.GET.get(param)
            }

            if captured:
                existing = request.session.get(self.SESSION_KEY) or {}
                # First touch wins — don't overwrite an earlier paid click.
                if not existing.get('gclid'):
                    captured['landing_page'] = request.build_absolute_uri()[:500]
                    captured['referrer'] = request.META.get('HTTP_REFERER', '')[:500]
                    existing.update(captured)
                    request.session[self.SESSION_KEY] = existing

        return self.get_response(request)


class ContentSecurityPolicyMiddleware:
    """Adds Content-Security-Policy header to all responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Content-Security-Policy: Allow our own resources + trusted CDNs
        #
        # Google Ads conversion tracking does NOT run on googletagmanager.com
        # alone. gtag/GTM loads a second script from googleadservices.com,
        # which then pings googleads.g.doubleclick.net and drops a conversion
        # iframe from td.doubleclick.net. If those three hosts are missing
        # here the browser blocks them and Google Ads records zero
        # conversions, even though the tag itself is installed correctly.
        google_ads_hosts = (
            "https://www.googleadservices.com "
            "https://googleads.g.doubleclick.net "
            "https://td.doubleclick.net"
        )

        csp = (
            "default-src 'self'; "
            f"script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdnjs.cloudflare.com https://www.googletagmanager.com https://www.google-analytics.com https://static.cloudflareinsights.com {google_ads_hosts}; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            f"connect-src 'self' https://www.google-analytics.com https://www.googletagmanager.com https://analytics.google.com https://stats.g.doubleclick.net {google_ads_hosts}; "
            f"frame-src 'self' https://www.googletagmanager.com {google_ads_hosts}; "
            "frame-ancestors 'self';"
        )
        response['Content-Security-Policy'] = csp

        # Permissions-Policy: Restrict browser features
        response['Permissions-Policy'] = (
            "camera=(), microphone=(), geolocation=(self), payment=()"
        )

        return response
