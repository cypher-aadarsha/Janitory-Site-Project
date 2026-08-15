"""
Tests covering the lead capture path end to end.

These exist because the contact form has silently broken before (a field
name mismatch meant every submission failed validation while the page still
looked normal). A broken lead form is expensive and invisible, so the happy
path is asserted here rather than trusted.
"""
import logging

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Booking, Service, SiteSetting


class GoogleTagRenderingTests(TestCase):
    """The tracking tags must be present on every public page."""

    @override_settings(
        GOOGLE_ANALYTICS_ID='G-TESTGA1234',
        GOOGLE_ADS_CONVERSION_ID='AW-1234567890',
    )
    def test_google_tag_renders_on_public_pages(self):
        for name in ('home', 'about', 'services', 'contact', 'careers'):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                content = response.content.decode()
                self.assertContains(response, 'googletagmanager.com/gtag/js')
                self.assertIn("gtag('config', 'G-TESTGA1234')", content)
                self.assertIn("gtag('config', 'AW-1234567890')", content)

    @override_settings(GOOGLE_ANALYTICS_ID='', GOOGLE_ADS_CONVERSION_ID='')
    def test_tags_omitted_when_ids_blank(self):
        """Local/staging runs with blank IDs must not hit the live accounts."""
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, 'googletagmanager.com/gtag/js')

    @override_settings(
        GOOGLE_ADS_CONVERSION_ID='AW-1234567890',
        GOOGLE_ADS_CALL_CONVERSION_LABEL='TestCallLabel',
    )
    def test_call_conversion_wired_when_label_present(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'AW-1234567890/TestCallLabel')

    @override_settings(
        GOOGLE_ADS_CONVERSION_ID='AW-1234567890',
        GOOGLE_ADS_CALL_CONVERSION_LABEL='',
    )
    def test_no_conversion_fired_without_label(self):
        """A send_to without a label is invalid and would report nothing."""
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, "'send_to'")


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class BookingSubmissionTests(TestCase):

    def setUp(self):
        self.service = Service.objects.create(
            title='Commercial Cleaning',
            slug='commercial-cleaning',
            description='Test service',
        )
        SiteSetting.objects.create(contact_email='owner@example.com')
        self.payload = {
            'name': 'Jane Doe',
            'email': 'jane@example.com',
            'phone': '5105551234',
            'address': '123 Main St, Oakland, CA 94607',
            'service': self.service.pk,
            'preferred_date': '2030-01-15',
            'preferred_time': '09:00',
            'notes': 'Front door code is 1234.',
        }

    def test_valid_submission_saves_booking(self):
        response = self.client.post(reverse('contact'), self.payload)

        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.get()
        self.assertEqual(booking.name, 'Jane Doe')
        self.assertEqual(booking.service, self.service)
        self.assertEqual(booking.status, 'PENDING')
        self.assertRedirects(
            response,
            f'/contact/?success=1&ref={booking.pk}',
            fetch_redirect_response=False,
        )

    def test_valid_submission_sends_notification_email(self):
        self.client.post(reverse('contact'), self.payload)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn('Jane Doe', message.subject)
        self.assertIn('5105551234', message.body)
        self.assertEqual(message.to, ['owner@example.com'])
        self.assertEqual(message.reply_to, ['jane@example.com'])

    def test_invalid_submission_does_not_save_or_redirect(self):
        bad_payload = dict(self.payload, name='', email='not-an-email')
        response = self.client.post(reverse('contact'), bad_payload)

        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_failure_does_not_lose_the_lead(self):
        """A mail outage must never cost us a captured lead."""
        # The failure is logged by design; silence it so the expected
        # traceback doesn't look like a broken test run.
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

        with override_settings(
            EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
            EMAIL_HOST='127.0.0.1',
            EMAIL_PORT=1,
            EMAIL_HOST_USER='someone@example.com',
        ):
            response = self.client.post(reverse('contact'), self.payload)

        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(response.status_code, 302)

    @override_settings(
        GOOGLE_ADS_CONVERSION_ID='AW-1234567890',
        GOOGLE_ADS_LEAD_CONVERSION_LABEL='TestLeadLabel',
    )
    def test_conversion_fires_only_on_success_page(self):
        plain = self.client.get(reverse('contact'))
        self.assertNotContains(plain, 'AW-1234567890/TestLeadLabel')

        self.client.post(reverse('contact'), self.payload)
        booking = Booking.objects.get()
        success = self.client.get(f'/contact/?success=1&ref={booking.pk}')

        self.assertContains(success, 'AW-1234567890/TestLeadLabel')
        self.assertContains(success, 'generate_lead')
        # transaction_id lets Google Ads de-duplicate a refreshed success page.
        self.assertContains(success, f"'transaction_id': '{booking.pk}'")


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AttributionTests(TestCase):
    """A lead is only useful for ad spend decisions if we know its source."""

    def setUp(self):
        self.service = Service.objects.create(
            title='Janitorial', slug='janitorial', description='Test'
        )
        SiteSetting.objects.create(contact_email='owner@example.com')
        self.payload = {
            'name': 'Paid Visitor',
            'email': 'paid@example.com',
            'phone': '5105559999',
            'address': '9 Broadway, Oakland, CA',
            'service': self.service.pk,
            'preferred_date': '2030-02-01',
            'preferred_time': '10:30',
            'notes': '',
        }

    def test_gclid_from_landing_page_is_attached_to_booking(self):
        # Visitor arrives on an ad click, browses, then converts on /contact/.
        self.client.get('/?gclid=TestClickId123&utm_source=google&utm_medium=cpc')
        self.client.get(reverse('services'))
        self.client.post(reverse('contact'), self.payload)

        booking = Booking.objects.get()
        self.assertEqual(booking.gclid, 'TestClickId123')
        self.assertEqual(booking.utm_source, 'google')
        self.assertEqual(booking.utm_medium, 'cpc')
        self.assertTrue(booking.is_paid_lead)

    def test_first_touch_attribution_is_not_overwritten(self):
        self.client.get('/?gclid=FirstClick')
        self.client.get('/?utm_source=newsletter&utm_medium=email')
        self.client.post(reverse('contact'), self.payload)

        self.assertEqual(Booking.objects.get().gclid, 'FirstClick')

    def test_organic_lead_has_no_attribution(self):
        self.client.get(reverse('home'))
        self.client.post(reverse('contact'), self.payload)

        booking = Booking.objects.get()
        self.assertEqual(booking.gclid, '')
        self.assertFalse(booking.is_paid_lead)

    def test_attribution_included_in_notification_email(self):
        self.client.get('/?gclid=TestClickId123')
        self.client.post(reverse('contact'), self.payload)

        self.assertIn('GOOGLE ADS CLICK', mail.outbox[0].body)


class ContentSecurityPolicyTests(TestCase):
    """
    The CSP must allow the hosts Google Ads conversion tracking actually
    uses. Missing these blocks conversions in the browser even when the tag
    is installed correctly.
    """

    REQUIRED_HOSTS = (
        'https://www.googleadservices.com',
        'https://googleads.g.doubleclick.net',
        'https://td.doubleclick.net',
    )

    def test_google_ads_hosts_allowed(self):
        csp = self.client.get(reverse('home'))['Content-Security-Policy']
        directives = dict(
            (part.strip().split(' ', 1) + [''])[:2]
            for part in csp.split(';') if part.strip()
        )

        for directive in ('script-src', 'connect-src', 'frame-src'):
            for host in self.REQUIRED_HOSTS:
                with self.subTest(directive=directive, host=host):
                    self.assertIn(host, directives[directive])
