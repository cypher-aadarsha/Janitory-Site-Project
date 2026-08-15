from django.conf import settings as django_settings
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


def google_tracking(request):
    """
    Exposes the Google tracking IDs to every template so the tags render on
    every page from a single place (base.html) rather than being pasted per
    page and drifting out of sync.

    Each value is blank-able: an empty ID means that tag is simply not
    rendered, which keeps local development and staging out of the
    production Analytics and Ads accounts.
    """
    ads_conversion_id = getattr(django_settings, 'GOOGLE_ADS_CONVERSION_ID', '')
    lead_label = getattr(django_settings, 'GOOGLE_ADS_LEAD_CONVERSION_LABEL', '')
    call_label = getattr(django_settings, 'GOOGLE_ADS_CALL_CONVERSION_LABEL', '')

    def send_to(label):
        """Build the 'send_to' value Google Ads expects: AW-XXXX/label."""
        if ads_conversion_id and label:
            return f'{ads_conversion_id}/{label}'
        return ''

    return {
        'GA_MEASUREMENT_ID': getattr(django_settings, 'GOOGLE_ANALYTICS_ID', ''),
        'GTM_CONTAINER_ID': getattr(django_settings, 'GOOGLE_TAG_MANAGER_ID', ''),
        'ADS_CONVERSION_ID': ads_conversion_id,
        'ADS_LEAD_SEND_TO': send_to(lead_label),
        'ADS_CALL_SEND_TO': send_to(call_label),
    }
