"""
Custom security middleware for adding Content-Security-Policy header.
"""


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
