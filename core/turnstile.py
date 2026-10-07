"""
Server-side verification for Cloudflare Turnstile.

Blank-able like the tracking IDs: with no secret key configured (local dev,
tests) verification is skipped and the widget is not rendered.
"""
import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'


def is_enabled():
    return bool(settings.TURNSTILE_SITE_KEY and settings.TURNSTILE_SECRET_KEY)


def verify(token):
    """
    True when the visitor passed the challenge.

    Cloudflare explicitly rejecting the token is the only thing that blocks a
    lead. If the verification call itself fails (network error, Cloudflare
    outage) we let the lead through: losing a paying customer to a CAPTCHA
    outage costs more than one spam submission slipping past it.
    """
    if not is_enabled():
        return True
    if not token:
        return False

    data = urllib.parse.urlencode({
        'secret': settings.TURNSTILE_SECRET_KEY,
        'response': token,
    }).encode()
    try:
        with urllib.request.urlopen(
            urllib.request.Request(VERIFY_URL, data=data), timeout=5
        ) as response:
            return bool(json.loads(response.read().decode()).get('success'))
    except Exception:
        logger.exception("Turnstile verification unavailable; letting the submission through.")
        return True
