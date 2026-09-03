"""
Server-side GA4 Measurement Protocol client.

Used to report events that happen with no browser present: a staff member
changing a booking's status in the CMS dashboard has no gtag/dataLayer to
push to, so GA4 -- and, through it, the linked Google Ads account -- would
never learn a lead was qualified or converted without this.

Deliberately uses urllib from the standard library rather than requests,
matching core/email_backends.py, to avoid adding a dependency for one HTTP
call.

Best-effort like the lead notification email: a booking status change must
never fail because Google's endpoint is slow or down.
"""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

MP_ENDPOINT = 'https://www.google-analytics.com/mp/collect'
TIMEOUT = 5


def send_ga4_event(client_id, event_name, params=None):
    """
    Send a single GA4 Measurement Protocol event tied to an existing
    client_id captured from the visitor's browser session.

    Returns True on a 2xx response, False otherwise. Callers must treat this
    as best-effort and never let a False stop whatever they were already
    doing (e.g. saving a booking's status).
    """
    measurement_id = getattr(settings, 'GOOGLE_ANALYTICS_ID', '')
    api_secret = getattr(settings, 'GA4_API_SECRET', '')

    if not measurement_id or not api_secret:
        logger.warning(
            "GA4 Measurement Protocol not configured (missing "
            "GOOGLE_ANALYTICS_ID or GA4_API_SECRET); '%s' was not sent.",
            event_name,
        )
        return False

    if not client_id:
        logger.warning(
            "No GA4 client_id available on this booking; '%s' was not sent.",
            event_name,
        )
        return False

    payload = {
        'client_id': client_id,
        'events': [{
            'name': event_name,
            'params': params or {},
        }],
    }

    url = f'{MP_ENDPOINT}?measurement_id={measurement_id}&api_secret={api_secret}'
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'content-type': 'application/json'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            if 200 <= response.status < 300:
                return True
            logger.error(
                "GA4 Measurement Protocol returned HTTP %s for '%s'.",
                response.status, event_name,
            )
    except urllib.error.HTTPError as exc:
        logger.error(
            "GA4 Measurement Protocol rejected '%s' (HTTP %s).",
            event_name, exc.code,
        )
    except Exception:
        logger.exception(
            "Failed to reach GA4 Measurement Protocol for '%s'.", event_name
        )

    return False
