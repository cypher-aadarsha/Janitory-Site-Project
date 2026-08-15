"""
Lead notification emails.

Form submissions were previously saved to the database and nothing else
happened — no email, no alert. Unless somebody logged into the CMS and
checked, a lead could sit unseen for days, which looks identical to
"we aren't getting any leads".

Every send here is best-effort: the lead is already committed to the
database before we try to send, and a mail failure must never turn a
captured lead into an error page for the customer.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from .models import SiteSetting

logger = logging.getLogger(__name__)


def _recipients():
    """
    Who gets notified. Prefers the explicit LEAD_NOTIFICATION_EMAILS setting,
    otherwise falls back to the contact email configured in the CMS.
    """
    configured = getattr(settings, 'LEAD_NOTIFICATION_EMAILS', [])
    if configured:
        return configured

    site_setting = SiteSetting.objects.first()
    if site_setting and site_setting.contact_email:
        return [site_setting.contact_email]

    return []


def _is_email_configured():
    """
    True when there is a real mail backend to send through. Avoids logging a
    scary traceback on local development where SMTP was never set up.
    """
    backend = getattr(settings, 'EMAIL_BACKEND', '')
    if 'smtp' not in backend:
        # console/locmem/file backends are always usable
        return True
    return bool(getattr(settings, 'EMAIL_HOST_USER', ''))


def _send(subject, body, reply_to=None):
    recipients = _recipients()
    if not recipients:
        logger.warning("Lead notification skipped: no recipient configured.")
        return False

    if not _is_email_configured():
        logger.warning(
            "Lead notification skipped: EMAIL_HOST_USER is not set. "
            "The lead was saved but nobody was emailed."
        )
        return False

    try:
        connection = get_connection(fail_silently=False)
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
            reply_to=reply_to or None,
            connection=connection,
        )
        message.send()
        return True
    except Exception:
        # Never let a mail problem surface to the customer — the lead is
        # already saved, and losing the notification is recoverable via CMS.
        logger.exception("Failed to send lead notification email.")
        return False


def notify_new_booking(booking):
    """Email the team when a booking request comes in through the site."""
    service = booking.service.title if booking.service else "Not specified"

    attribution = "Organic / direct"
    if booking.gclid:
        attribution = f"GOOGLE ADS CLICK (gclid: {booking.gclid})"
    elif booking.utm_source:
        attribution = (
            f"{booking.utm_source} / {booking.utm_medium or 'n/a'}"
            f" — campaign: {booking.utm_campaign or 'n/a'}"
        )

    subject = f"New Booking Request — {booking.name} ({service})"
    body = f"""A new booking request was submitted on the website.

CUSTOMER
  Name:     {booking.name}
  Phone:    {booking.phone}
  Email:    {booking.email}
  Address:  {booking.address}

REQUEST
  Service:  {service}
  Date:     {booking.preferred_date}
  Time:     {booking.preferred_time}
  Notes:    {booking.notes or "(none)"}

SOURCE
  {attribution}
  Landing page: {booking.landing_page or "n/a"}

Received: {booking.created_at:%Y-%m-%d %H:%M %Z}
Manage this lead in the CMS dashboard under Bookings.
"""
    return _send(subject, body, reply_to=[booking.email] if booking.email else None)


def notify_new_application(application):
    """Email the team when a careers application comes in."""
    subject = f"New Job Application — {application.name} ({application.position})"
    body = f"""A new job application was submitted on the website.

APPLICANT
  Name:      {application.name}
  Phone:     {application.phone}
  Email:     {application.email}
  Position:  {application.position}
  Resume:    {application.resume_link or "(not provided)"}

COVER LETTER
{application.cover_letter or "(none)"}

Received: {application.created_at:%Y-%m-%d %H:%M %Z}
Manage this application in the CMS dashboard under Applications.
"""
    return _send(subject, body, reply_to=[application.email] if application.email else None)
