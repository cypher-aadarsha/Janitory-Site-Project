"""
Email backends that send over HTTPS instead of SMTP.

DigitalOcean blocks outbound SMTP (ports 25, 465, 587 and 2525) at the
network edge, so Django's stock SMTP backend cannot open a connection from
the droplet at all -- it fails with "Network is unreachable" before it ever
gets as far as authenticating. Port 443 is not blocked, so relaying through
a provider's HTTP API sidesteps the restriction entirely.

Selected via EMAIL_BACKEND in .env:

    EMAIL_BACKEND=core.email_backends.BrevoAPIBackend

Removing that line falls back to Django's SMTP backend, which is what we
want if the hosting block is ever lifted. Nothing else needs to change --
the notification code calls django.core.mail either way.

Deliberately uses urllib from the standard library rather than requests, to
avoid adding a dependency for one HTTP call.
"""
import json
import logging
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

BREVO_ENDPOINT = 'https://api.brevo.com/v3/smtp/email'


def _address(value):
    """
    Turn 'Some Name <someone@example.com>' into Brevo's {name, email} shape.
    A bare address is passed through with no name.
    """
    name, email = parseaddr(value or '')
    entry = {'email': email}
    if name:
        entry['name'] = name
    return entry


class BrevoAPIBackend(BaseEmailBackend):
    """
    Sends mail through Brevo's transactional email API over HTTPS.

    Honours fail_silently the same way Django's own backends do, so a
    provider outage raises nothing into the request path -- the caller in
    core/notifications.py already treats delivery as best-effort and commits
    the lead before attempting to send.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = getattr(settings, 'BREVO_API_KEY', '')
        self.timeout = getattr(settings, 'EMAIL_TIMEOUT', 10) or 10

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not self.api_key:
            logger.warning(
                "BrevoAPIBackend: BREVO_API_KEY is not set, sending nothing."
            )
            if not self.fail_silently:
                raise ValueError("BREVO_API_KEY is not configured.")
            return 0

        sent = 0
        for message in email_messages:
            if self._send(message):
                sent += 1
        return sent

    def _payload(self, message):
        """Build the JSON body Brevo expects from a Django EmailMessage."""
        sender = message.from_email or settings.DEFAULT_FROM_EMAIL

        payload = {
            'sender': _address(sender),
            'to': [_address(addr) for addr in message.to],
            'subject': message.subject,
            'textContent': message.body or '',
        }

        if message.cc:
            payload['cc'] = [_address(addr) for addr in message.cc]
        if message.bcc:
            payload['bcc'] = [_address(addr) for addr in message.bcc]
        if message.reply_to:
            # Brevo accepts a single reply-to address.
            payload['replyTo'] = _address(message.reply_to[0])

        # Pick up an HTML alternative when the caller attached one.
        for content, mimetype in getattr(message, 'alternatives', []) or []:
            if mimetype == 'text/html':
                payload['htmlContent'] = content
                break

        return payload

    def _send(self, message):
        if not message.to:
            return False

        request = urllib.request.Request(
            BREVO_ENDPOINT,
            data=json.dumps(self._payload(message)).encode('utf-8'),
            headers={
                'api-key': self.api_key,
                'content-type': 'application/json',
                'accept': 'application/json',
            },
            method='POST',
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if 200 <= response.status < 300:
                    return True
                logger.error(
                    "Brevo returned HTTP %s when sending mail.", response.status
                )
        except urllib.error.HTTPError as exc:
            # Read the body: Brevo explains rejections (unverified sender,
            # bad key, quota) in the response, and that detail is the
            # difference between a five-minute fix and an afternoon.
            detail = ''
            try:
                detail = exc.read().decode('utf-8', 'replace')[:500]
            except Exception:
                pass
            logger.error("Brevo rejected the message (HTTP %s): %s", exc.code, detail)
        except Exception:
            logger.exception("Failed to reach the Brevo API.")

        if not self.fail_silently:
            raise RuntimeError("Brevo API send failed; see logs for detail.")
        return False
