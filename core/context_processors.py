from django.core.cache import cache
from .models import SiteSetting


def site_settings(request):
    """
    Context processor that provides site settings to all templates.
    Uses Django's cache framework to avoid hitting the database on every request.
    Cache is invalidated after 5 minutes or when settings are updated.
    """
    settings = cache.get('site_settings')
    if settings is None:
        settings = SiteSetting.objects.first()
        # Cache for 5 minutes (300 seconds)
        cache.set('site_settings', settings, 300)
    return {'site_settings': settings}
