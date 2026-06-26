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


class ContentSecurityPolicyMiddleware:
    """Adds Content-Security-Policy header to all responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Content-Security-Policy: Allow our own resources + trusted CDNs
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdnjs.cloudflare.com https://www.googletagmanager.com https://www.google-analytics.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://www.google-analytics.com; "
            "frame-ancestors 'self';"
        )
        response['Content-Security-Policy'] = csp

        # Permissions-Policy: Restrict browser features
        response['Permissions-Policy'] = (
            "camera=(), microphone=(), geolocation=(self), payment=()"
        )

        return response
