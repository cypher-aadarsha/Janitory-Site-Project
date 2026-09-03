"""
Reports a Booking's status lifecycle to GA4 so Google Ads can optimize
toward leads that actually turn into customers, not just form submissions.

The initial 'generate_lead' conversion (contact.html) is fired client-side
at submission time. Everything after that -- a staff member deciding a lead
is real (PENDING -> CONFIRMED) or that the job closed (CONFIRMED ->
COMPLETED) -- happens later from the CMS dashboard, with no browser present.
These signals catch that save and report it server-side instead.

Connected from CoreConfig.ready() (core/apps.py), which is the standard
place to wire up signal handlers -- importing this module at load time, as a
decorator would require, runs before the app registry is populated.
"""
import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .ga4 import send_ga4_event
from .models import Booking

logger = logging.getLogger(__name__)

# (previous status, new status) -> (GA4 event name, "already reported" field)
STATUS_TRANSITION_EVENTS = {
    ('PENDING', 'CONFIRMED'): ('qualify_lead', 'qualify_lead_reported'),
    ('CONFIRMED', 'COMPLETED'): ('close_convert_lead', 'close_convert_lead_reported'),
}


@receiver(pre_save, sender=Booking)
def stash_previous_status(sender, instance, **kwargs):
    """Record the status this row had before this save, if any."""
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        instance._previous_status = (
            Booking.objects.only('status').get(pk=instance.pk).status
        )
    except Booking.DoesNotExist:
        instance._previous_status = None


@receiver(post_save, sender=Booking)
def report_status_transition(sender, instance, created, **kwargs):
    if created:
        return

    previous = getattr(instance, '_previous_status', None)
    if previous is None or previous == instance.status:
        return

    mapping = STATUS_TRANSITION_EVENTS.get((previous, instance.status))
    if not mapping:
        return

    event_name, reported_field = mapping
    if getattr(instance, reported_field):
        # Already reported once for this booking; a status that flapped
        # back and forth must not double-count the same conversion.
        return

    params = {'transaction_id': str(instance.pk)}
    if event_name == 'close_convert_lead':
        params['currency'] = 'USD'
        params['value'] = float(instance.lifetime_value or 0)

    send_ga4_event(instance.ga_client_id, event_name, params)

    # Mark as reported regardless of whether the send actually succeeded --
    # matches notify_new_booking's best-effort contract elsewhere in this
    # app: no retry queue, and re-firing on every later unrelated save would
    # itself become a source of duplicate conversions. Uses .update() to
    # avoid re-entering this same signal, and also sets it on the in-memory
    # instance so the guard above is still correct if the same Python object
    # gets saved again (a fresh fetch per request, as the CMS view does,
    # would see it either way).
    Booking.objects.filter(pk=instance.pk).update(**{reported_field: True})
    setattr(instance, reported_field, True)
