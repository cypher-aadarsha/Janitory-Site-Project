"""
Tests covering the lead capture path end to end.

These exist because the contact form has silently broken before (a field
name mismatch meant every submission failed validation while the page still
looked normal). A broken lead form is expensive and invisible, so the happy
path is asserted here rather than trusted.
"""
import json
import logging
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import BookingForm
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
            'company_name': 'Acme Corp',
            'facility_size': '2500_10000',
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

    @override_settings(
        GOOGLE_ADS_CONVERSION_ID='AW-1234567890',
        GOOGLE_ADS_LEAD_CONVERSION_LABEL='TestLeadLabel',
    )
    def test_conversion_does_not_refire_on_reload(self):
        """
        A refresh or back-button hit on the confirmation page must not
        report a second conversion for the same lead -- Google Ads would
        otherwise double-count one real booking.
        """
        self.client.post(reverse('contact'), self.payload)
        booking = Booking.objects.get()
        url = f'/contact/?success=1&ref={booking.pk}'

        first_load = self.client.get(url)
        second_load = self.client.get(url)

        self.assertContains(first_load, 'generate_lead')
        self.assertNotContains(second_load, 'generate_lead')
        self.assertNotContains(second_load, 'AW-1234567890/TestLeadLabel')
        # The confirmation page itself still renders fine on reload.
        self.assertEqual(second_load.status_code, 200)

    @override_settings(
        GOOGLE_ADS_CONVERSION_ID='AW-1234567890',
        GOOGLE_ADS_LEAD_CONVERSION_LABEL='TestLeadLabel',
    )
    def test_forged_success_url_does_not_fire_a_conversion(self):
        """
        /contact/?success=1&ref=<anything> is guessable and must not be able
        to report a fake conversion (or leak another lead's email/phone) on
        its own, with no real submission behind it.
        """
        self.client.post(reverse('contact'), self.payload)
        real_booking = Booking.objects.get()

        forged = self.client.get('/contact/?success=1&ref=999999')

        self.assertNotContains(forged, 'generate_lead')
        self.assertNotContains(forged, 'AW-1234567890/TestLeadLabel')
        self.assertNotContains(forged, real_booking.email)

    @override_settings(
        GOOGLE_ADS_CONVERSION_ID='AW-1234567890',
        GOOGLE_ADS_LEAD_CONVERSION_LABEL='TestLeadLabel',
    )
    def test_enhanced_conversion_user_data_sent_on_success(self):
        """Email/phone from the submission is handed to gtag for Enhanced
        Conversions matching, normalized (lowercased email, E.164 phone)."""
        self.client.post(reverse('contact'), self.payload)
        booking = Booking.objects.get()
        success = self.client.get(f'/contact/?success=1&ref={booking.pk}')

        self.assertContains(success, "gtag('set', 'user_data'")
        self.assertContains(success, "'email': 'jane@example.com'")
        self.assertContains(success, "'phone_number': '+15105551234'")

    def test_ga_client_id_captured_from_hidden_field(self):
        payload = dict(self.payload, ga_client_id='123456789.987654321')
        self.client.post(reverse('contact'), payload)

        self.assertEqual(Booking.objects.get().ga_client_id, '123456789.987654321')


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
            'company_name': 'Acme Corp',
            'facility_size': '2500_10000',
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

    def test_gtag_connect_hosts_allowed(self):
        csp = self.client.get(reverse('home'))['Content-Security-Policy']
        connect_src = next(
            part.strip() for part in csp.split(';')
            if part.strip().startswith('connect-src')
        )

        for host in ('https://ad.doubleclick.net', 'https://www.google.com'):
            with self.subTest(host=host):
                self.assertIn(host, connect_src)


class LeadQualificationTests(TestCase):
    """Company, phone and facility-size rules on the contact form."""

    def setUp(self):
        self.service = Service.objects.create(
            title='Office Cleaning', slug='office-cleaning', description='d'
        )
        SiteSetting.objects.create(contact_email='owner@example.com')
        self.payload = {
            'name': 'Pat Smith',
            'email': 'pat@example.com',
            'phone': '(510) 555-1234',
            'company_name': 'Smith & Co',
            'facility_size': '10000_50000',
            'address': '1 Market St, Oakland, CA',
            'service': self.service.pk,
            'preferred_date': '2030-05-01',
            'preferred_time': '09:00',
            'notes': '',
        }

    def _post(self, **overrides):
        return self.client.post(reverse('contact'), dict(self.payload, **overrides))

    def test_formatted_us_phone_is_accepted(self):
        for phone in ('(510) 555-1234', '510-555-1234', '510.555.1234', '+1 510 555 1234', '15105551234'):
            with self.subTest(phone=phone):
                self.assertTrue(BookingForm(dict(self.payload, phone=phone)).is_valid())

    def test_invalid_phones_are_rejected(self):
        for phone in ('1234567', 'call me', '555555555', '5555555555', '0105551234', '5100551234', '51055512345678'):
            with self.subTest(phone=phone):
                form = BookingForm(dict(self.payload, phone=phone))
                self.assertFalse(form.is_valid())
                self.assertIn('phone', form.errors)

    def test_company_name_is_required(self):
        for company in ('', '   ', 'x', '--'):
            with self.subTest(company=company):
                response = self._post(company_name=company)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(Booking.objects.count(), 0)

    def test_facility_size_is_required_and_must_be_a_valid_choice(self):
        for size in ('', 'HUGE'):
            with self.subTest(size=size):
                response = self._post(facility_size=size)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(Booking.objects.count(), 0)

    def test_validation_errors_are_shown_to_the_visitor(self):
        response = self._post(phone='123', company_name='')
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('Phone' in m for m in messages))
        self.assertTrue(any('Company name' in m for m in messages))

    def test_submitted_values_survive_a_validation_error(self):
        response = self._post(phone='123')
        self.assertContains(response, 'value="Smith &amp; Co"')

    def test_company_and_size_are_saved_and_emailed(self):
        self._post()
        booking = Booking.objects.get()
        self.assertEqual(booking.company_name, 'Smith & Co')
        self.assertEqual(booking.facility_size, '10000_50000')
        self.assertFalse(booking.is_low_fit)
        self.assertIn('Smith & Co', mail.outbox[0].body)
        self.assertNotIn('LOW FIT', mail.outbox[0].body)

    def test_low_fit_lead_is_accepted_but_flagged(self):
        response = self._post(facility_size='UNDER_2500')
        booking = Booking.objects.get()
        self.assertTrue(booking.is_low_fit)
        self.assertRedirects(
            response, f'/contact/?success=1&ref={booking.pk}',
            fetch_redirect_response=False,
        )
        self.assertIn('LOW FIT', mail.outbox[0].body)


@override_settings(TURNSTILE_SITE_KEY='site-key', TURNSTILE_SECRET_KEY='secret-key')
class TurnstileTests(TestCase):
    """The CAPTCHA blocks bots without ever costing a real lead."""

    def setUp(self):
        self.service = Service.objects.create(
            title='Floor Care', slug='floor-care', description='d'
        )
        SiteSetting.objects.create(contact_email='owner@example.com')
        self.payload = {
            'name': 'Bot Or Not',
            'email': 'bot@example.com',
            'phone': '5105551234',
            'company_name': 'Acme Corp',
            'facility_size': '2500_10000',
            'address': '2 Market St, Oakland, CA',
            'service': self.service.pk,
            'preferred_date': '2030-06-01',
            'preferred_time': '09:00',
            'notes': '',
            'cf-turnstile-response': 'token-from-widget',
        }

    def _siteverify(self, success):
        response = mock.MagicMock()
        response.read.return_value = json.dumps({'success': success}).encode()
        response.__enter__.return_value = response
        return response

    def test_widget_is_rendered_when_configured(self):
        response = self.client.get(reverse('contact'))
        self.assertContains(response, 'class="cf-turnstile"')
        self.assertContains(response, 'data-sitekey="site-key"')
        self.assertContains(response, 'challenges.cloudflare.com/turnstile/v0/api.js')

    @override_settings(TURNSTILE_SITE_KEY='', TURNSTILE_SECRET_KEY='')
    def test_widget_is_hidden_when_not_configured(self):
        self.assertNotContains(self.client.get(reverse('contact')), 'cf-turnstile')

    @mock.patch('core.turnstile.urllib.request.urlopen')
    def test_passing_the_challenge_saves_the_lead(self, mock_urlopen):
        mock_urlopen.return_value = self._siteverify(True)
        self.client.post(reverse('contact'), self.payload)
        self.assertEqual(Booking.objects.count(), 1)

    @mock.patch('core.turnstile.urllib.request.urlopen')
    def test_failing_the_challenge_blocks_the_lead(self, mock_urlopen):
        mock_urlopen.return_value = self._siteverify(False)
        response = self.client.post(reverse('contact'), self.payload)
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch('core.turnstile.urllib.request.urlopen')
    def test_missing_token_blocks_without_calling_cloudflare(self, mock_urlopen):
        payload = dict(self.payload)
        del payload['cf-turnstile-response']
        self.client.post(reverse('contact'), payload)
        self.assertEqual(Booking.objects.count(), 0)
        mock_urlopen.assert_not_called()

    @mock.patch('core.turnstile.urllib.request.urlopen', side_effect=OSError('network down'))
    def test_cloudflare_outage_does_not_lose_the_lead(self, mock_urlopen):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.client.post(reverse('contact'), self.payload)
        self.assertEqual(Booking.objects.count(), 1)

    def test_csp_allows_turnstile(self):
        csp = self.client.get(reverse('home'))['Content-Security-Policy']
        directives = dict(
            (part.strip().split(' ', 1) + [''])[:2]
            for part in csp.split(';') if part.strip()
        )
        for directive in ('script-src', 'frame-src'):
            with self.subTest(directive=directive):
                self.assertIn('https://challenges.cloudflare.com', directives[directive])


@override_settings(
    EMAIL_BACKEND='core.email_backends.BrevoAPIBackend',
    BREVO_API_KEY='test-key',
    DEFAULT_FROM_EMAIL='sender@example.com',
)
class BrevoBackendTests(TestCase):
    """
    The droplet's host blocks outbound SMTP, so lead mail relays over HTTPS
    instead. These cover the payload shape and, more importantly, that a
    provider failure still cannot cost us a lead.
    """

    def setUp(self):
        self.service = Service.objects.create(
            title='Pressure Washing', slug='pressure-washing', description='d'
        )
        SiteSetting.objects.create(contact_email='owner@example.com')
        self.payload = {
            'name': 'Api Lead',
            'email': 'api@example.com',
            'phone': '5105557777',
            'company_name': 'Acme Corp',
            'facility_size': '2500_10000',
            'address': '5 Franklin St, Oakland, CA',
            'service': self.service.pk,
            'preferred_date': '2030-04-01',
            'preferred_time': '14:00',
            'notes': '',
        }

    def _captured_request(self, mock_urlopen):
        self.assertTrue(mock_urlopen.called, "Brevo API was never called")
        request = mock_urlopen.call_args[0][0]
        return request, json.loads(request.data.decode())

    @mock.patch('core.email_backends.urllib.request.urlopen')
    def test_booking_sends_via_brevo_api(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.status = 201

        self.client.post(reverse('contact'), self.payload)

        request, body = self._captured_request(mock_urlopen)
        self.assertEqual(request.full_url, 'https://api.brevo.com/v3/smtp/email')
        self.assertEqual(request.get_header('Api-key'), 'test-key')
        self.assertEqual(body['sender']['email'], 'sender@example.com')
        self.assertEqual(body['to'], [{'email': 'owner@example.com'}])
        self.assertIn('Api Lead', body['subject'])
        self.assertIn('5105557777', body['textContent'])
        # Replying to the notification should reach the customer.
        self.assertEqual(body['replyTo']['email'], 'api@example.com')

    @mock.patch('core.email_backends.urllib.request.urlopen')
    def test_api_failure_does_not_lose_the_lead(self, mock_urlopen):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        mock_urlopen.side_effect = OSError("network is unreachable")

        response = self.client.post(reverse('contact'), self.payload)

        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(response.status_code, 302)

    @mock.patch('core.email_backends.urllib.request.urlopen')
    def test_missing_api_key_skips_send_without_crashing(self, mock_urlopen):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

        with override_settings(BREVO_API_KEY=''):
            response = self.client.post(reverse('contact'), self.payload)

        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(mock_urlopen.called)

    def test_display_name_in_from_address_is_parsed(self):
        from .email_backends import _address
        self.assertEqual(
            _address('24 Hours Facility <hello@example.com>'),
            {'email': 'hello@example.com', 'name': '24 Hours Facility'},
        )
        self.assertEqual(_address('bare@example.com'), {'email': 'bare@example.com'})


class LeadLifecycleTrackingTests(TestCase):
    """
    qualify_lead / close_convert_lead: reported server-side (GA4 Measurement
    Protocol) when staff change a booking's status in the CMS, since no
    browser is present at that point to fire an event the normal way.
    """

    def setUp(self):
        self.service = Service.objects.create(
            title='Deep Cleaning', slug='deep-cleaning', description='d'
        )
        self.booking = Booking.objects.create(
            name='Lead One', email='lead@example.com', phone='5105550000',
            service=self.service, address='1 Test St',
            preferred_date='2030-01-01', preferred_time='09:00',
            ga_client_id='111111111.222222222',
        )

    @mock.patch('core.signals.send_ga4_event')
    def test_pending_to_confirmed_fires_qualify_lead(self, mock_send):
        self.booking.status = 'CONFIRMED'
        self.booking.save()

        mock_send.assert_called_once()
        client_id, event_name, params = mock_send.call_args[0]
        self.assertEqual(client_id, '111111111.222222222')
        self.assertEqual(event_name, 'qualify_lead')
        self.assertEqual(params['transaction_id'], str(self.booking.pk))

        self.booking.refresh_from_db()
        self.assertTrue(self.booking.qualify_lead_reported)
        self.assertFalse(self.booking.close_convert_lead_reported)

    @mock.patch('core.signals.send_ga4_event')
    def test_confirmed_to_completed_fires_close_convert_lead_with_value(self, mock_send):
        self.booking.status = 'CONFIRMED'
        self.booking.save()
        self.booking.lifetime_value = 250
        self.booking.status = 'COMPLETED'
        self.booking.save()

        event_name = mock_send.call_args_list[-1][0][1]
        params = mock_send.call_args_list[-1][0][2]
        self.assertEqual(event_name, 'close_convert_lead')
        self.assertEqual(params['currency'], 'USD')
        self.assertEqual(params['value'], 250.0)

    @mock.patch('core.signals.send_ga4_event')
    def test_unrelated_status_change_fires_nothing(self, mock_send):
        self.booking.status = 'CANCELLED'
        self.booking.save()

        mock_send.assert_not_called()

    @mock.patch('core.signals.send_ga4_event')
    def test_creating_a_booking_fires_nothing(self, mock_send):
        Booking.objects.create(
            name='Brand New', email='new@example.com', phone='5105551111',
            service=self.service, address='2 Test St',
            preferred_date='2030-01-02', preferred_time='10:00',
        )
        mock_send.assert_not_called()

    @mock.patch('core.signals.send_ga4_event')
    def test_flapping_status_does_not_double_report(self, mock_send):
        """
        A status corrected back and forth (e.g. COMPLETED marked in error,
        reverted, then marked COMPLETED again) must only report the
        conversion once -- otherwise one real sale is double-counted.
        """
        self.booking.status = 'CONFIRMED'
        self.booking.save()
        self.booking.status = 'COMPLETED'
        self.booking.save()
        self.booking.status = 'CONFIRMED'
        self.booking.save()
        self.booking.status = 'COMPLETED'
        self.booking.save()

        close_events = [
            call for call in mock_send.call_args_list
            if call[0][1] == 'close_convert_lead'
        ]
        self.assertEqual(len(close_events), 1)

    def test_missing_ga_client_id_is_logged_not_sent(self):
        """A booking with no captured client_id (e.g. a phone-in lead a
        staffer entered by hand) must not crash the status save."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

        booking = Booking.objects.create(
            name='No Client Id', email='none@example.com', phone='5105552222',
            service=self.service, address='3 Test St',
            preferred_date='2030-01-03', preferred_time='11:00',
        )
        booking.status = 'CONFIRMED'
        booking.save()  # must not raise

        booking.refresh_from_db()
        self.assertTrue(booking.qualify_lead_reported)

    @override_settings(GA4_API_SECRET='test-secret', GOOGLE_ANALYTICS_ID='G-TEST123')
    @mock.patch('core.ga4.urllib.request.urlopen')
    def test_ga4_measurement_protocol_payload_shape(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.status = 204

        self.booking.status = 'CONFIRMED'
        self.booking.save()

        request = mock_urlopen.call_args[0][0]
        self.assertIn('measurement_id=G-TEST123', request.full_url)
        self.assertIn('api_secret=test-secret', request.full_url)
        body = json.loads(request.data.decode())
        self.assertEqual(body['client_id'], '111111111.222222222')
        self.assertEqual(body['events'][0]['name'], 'qualify_lead')
