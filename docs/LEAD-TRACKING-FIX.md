# Lead Tracking & Conversion Fix

**Site:** 24 Hours Facility Maintenance Inc. — 24hoursfacilitymaintenance.com
**Date:** August 2026
**Status:** Deployed and verified in production

---

## The Problem

The business was running paid Google Ads campaigns but seeing **zero recorded
conversions** and receiving **no lead notifications**. Money was going out;
nothing measurable was coming back.

Investigation found this was not one bug. It was **four independent failures
stacked on top of each other** — any one alone would have hurt, and together
they made lead capture and measurement impossible end to end.

---

## Root Causes

### 1. The Google Ads tag was never on the site

`base.html` loaded a **Google Tag Manager container** (`GTM-K3K8Z87F`), but
GTM is only a container loader — an empty box. It is not the Google tag.

Neither the GA4 measurement ID (`G-JLBYG49T3E`) nor the Ads conversion ID
(`AW-18322970920`) appeared anywhere in the codebase. Google Ads had nothing
to count.

Confirmed by the Ads UI: `page_view`, `session_start` and `user_engagement`
all read **Inactive**. Those fire on every page load of a working setup, so
GA4 was receiving nothing at all — meaning the GTM container was empty.

### 2. The site's own CSP was blocking Google Ads

`janitorial_site/middleware.py` allowed only `googletagmanager.com` and
`google-analytics.com`.

Google Ads conversion tracking does not run on those hosts. It loads a second
script from `googleadservices.com`, which pings `googleads.g.doubleclick.net`
and drops a conversion iframe from `td.doubleclick.net`. None were allowed, so
**browsers silently blocked every conversion ping** — even if a tag had been
configured correctly inside GTM.

This is the one that would have kept conversions at zero even after fixing #1.

### 3. The contact form was completely broken until 22 July 2026

Commit `b223250` records it: a field-name mismatch (`service_id` vs `service`)
meant Django rejected **every single submission**. Visitors filled in the form,
got a validation error, and left.

Timeline: GTM installed 20 July, form fixed 22 July. So for the bulk of the ad
spend there were genuinely no leads to record.

### 4. Nothing ever sent an email

There was no email configuration anywhere in the project — no `EMAIL_BACKEND`,
no SMTP settings, no `send_mail` call. Bookings saved to the database and
nothing else happened.

Unless someone logged into `/dashboard/` and checked manually, a real lead was
indistinguishable from no lead.

---

## What Was Fixed

### Tracking

| Change | File |
|---|---|
| Added gtag.js with GA4 + Google Ads config to every page | `templates/base.html` |
| Fire Ads conversion only after a validated, saved booking | `templates/contact.html` |
| Added click-to-call and WhatsApp tracking | `templates/base.html` |
| Moved all tracking IDs into settings/env | `janitorial_site/settings.py` |
| Exposed tracking config to templates | `core/context_processors.py` |

The conversion fires on the `/contact/?success=1` success page, reached only
after `form.is_valid()` + `form.save()` + redirect. It carries the booking PK
as `transaction_id`, so refreshing the success page cannot double-count.

Phone links previously left no trace at all despite phone being the primary
lead channel for this business.

### Content Security Policy

Added to `script-src`, `connect-src` and `frame-src` in
`janitorial_site/middleware.py`:

- `https://www.googleadservices.com`
- `https://googleads.g.doubleclick.net`
- `https://td.doubleclick.net`

### Lead handling

| Change | File |
|---|---|
| Email the team on new bookings and job applications | `core/notifications.py` |
| Capture `gclid` / UTM on landing, carry in session | `janitorial_site/middleware.py` |
| Store attribution on the booking record | `core/models.py`, migration `0010` |
| Show lead source (PAID AD CLICK vs ORGANIC) in the CMS | `templates/cms/booking_detail.html` |
| HTTPS email backend for blocked-SMTP hosting | `core/email_backends.py` |

**Attribution is first-touch:** once a `gclid` is recorded for a session it is
not overwritten, so a later organic page view cannot erase paid attribution.

**Notifications are best-effort by design.** The booking is committed to the
database *before* the email is attempted, and failures are caught and logged.
A mail outage can cost a notification but never a lead.

---

## Google Ads Configuration

The existing conversion actions were all unusable:

- Five had source **"Website (Google Analytics (GA4))"** — imported from
  Analytics, so they carry **no conversion label** and cannot be fired from
  code.
- One had source **"Website"** but was created by Google's **automatic form
  detection**, which also exposes no event snippet, and cannot distinguish a
  successful save from a validation failure.

A new conversion action was created manually:

| Setting | Value |
|---|---|
| Name | Contact Form Submit |
| Source | Website (Manual event) |
| Category | Submit lead form |
| Count | One |
| Trigger | Page load |
| Click-through window | 90 days |
| Attribution | Data-driven |
| `send_to` | `AW-18322970920/wrJhCIeDn-IcEKiyiaFE` |

---

## Email Delivery

Gmail SMTP failed in production with `OSError: [Errno 101] Network is
unreachable`. Diagnosis showed:

- Outbound HTTPS worked (`HTTP/2 200` to Google)
- Ports 587, 465 and 2525 were all blocked
- `ufw` had no outbound restrictions
- DNS resolved IPv4 first, so not an IPv6 routing issue

**DigitalOcean blocks outbound SMTP at their network edge.** No droplet-side
configuration can change it.

Solution: `core/email_backends.py` adds `BrevoAPIBackend`, which relays over
**HTTPS port 443** via Brevo's transactional API. It uses `urllib` from the
standard library rather than adding a dependency for one HTTP call, and honours
`fail_silently`.

**Switching back is one line.** Remove `EMAIL_BACKEND` from `.env` and the
existing Gmail SMTP settings take over again — no code change, no redeploy.

---

## Database Migration Conflict

The production server carried two migrations that had never been committed:
`0008_alter_sitesetting_contact_email` and `0009_merge_20260722_1614`. Both were
applied to the live database, so the repository described a history the server
did not have.

Pulling would have placed **two different `0009` migrations** side by side and
`migrate` would have aborted with *"multiple leaf nodes in the migration
graph"* — leaving the new booking columns missing and **every form submission
failing with a 500 error**. Worse than not deploying at all.

Fixed by committing both server-only migrations and rebuilding the attribution
migration as `0010` on top of the merge, restoring a single linear graph.

---

## Test Coverage

`core/tests.py` — 18 tests, all passing:

- Google tag renders on every public page; omitted when IDs are blank
- Conversion fires **only** on the success page, never on page load
- No conversion sent when a label is unconfigured
- CSP allows all three Google Ads hosts across all three directives
- Valid submission saves the booking and redirects
- Invalid submission saves nothing and sends nothing
- **A mail failure never loses a captured lead**
- `gclid` survives landing → browsing → submission
- First-touch attribution is not overwritten
- Brevo receives the correct payload; API outage still saves the lead

Run with `python manage.py test core`.

---

## Deployment Record

| Item | Value |
|---|---|
| Server | DigitalOcean droplet, `138.68.47.235` |
| Live directory | `/var/www/janitorial_site` |
| Served by | gunicorn (3 workers) + nginx |
| Database | Managed PostgreSQL 18.4 |

**Note:** the droplet also holds `/var/www/Janitory-Site-Project` and
`/var/www/janitory`, neither of which is served. The live directory is
`janitorial_site` — confirmed via `systemctl cat gunicorn`. Deploying to the
folder matching the repository name would appear to succeed and change nothing.

### Deploy steps

```bash
cd /var/www/janitorial_site
cp .env .env.backup
DB_URL=$(grep '^DATABASE_URL=' .env | sed -e 's/^DATABASE_URL=//' -e 's/^"//' -e 's/"$//')
/usr/lib/postgresql/18/bin/pg_dump "$DB_URL" > /root/db-backup-$(date +%F-%H%M).sql

git pull origin main
venv/bin/pip install -r requirements.txt
nano .env                                     # append config
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput
systemctl restart gunicorn
```

`pg_dump` must be the v18 binary — Ubuntu's default v16 client refuses to dump
an 18.4 server.

### Verification

```bash
curl -s https://24hoursfacilitymaintenance.com/ | grep -c "AW-18322970920"
curl -sI https://24hoursfacilitymaintenance.com/ | grep -i "content-security-policy" | grep -c googleadservices
```

Both returned `1`. Test email delivered successfully.

---

## Commits

| Commit | Description |
|---|---|
| `685fc5f` | Fix Google Ads conversion tracking and lead notifications |
| `ac0dde3` | Add Google Ads lead conversion label |
| `20df071` | Add project notes covering commit attribution and lead tracking |
| `5251f6d` | Track server-only migrations, renumber attribution migration |
| `0f01ddf` | Relay lead notifications over HTTPS instead of blocked SMTP |

---

## Outstanding Items

### Do soon — affects data quality

- [ ] **Google Ads → Value:** change to "Use the same value for each
      conversion". Currently set to "different values", so every lead records
      as the $1 fallback.
- [ ] **Demote three conversion actions to Secondary:** `generate_lead`,
      `Submit lead form (Form submission…)`, and
      `Submit lead form (GA4 event form_submit)`. All are Primary alongside
      the new action, so **one lead can count up to three times**, making
      cost-per-lead look a third of reality.

### Security

- [ ] Rotate the PostgreSQL `doadmin` password
- [ ] Rotate the Gmail App Password
- [ ] Review DigitalOcean database **Trusted Sources**
- [ ] Reboot for the pending kernel update (`6.8.0-136` → `6.8.0-137`)

### Improvements

- [ ] **Phone-call tracking.** Reformat the CMS contact number to
      `(510) 409-6697` first — Google cannot detect an unformatted
      `5104096697` to swap in a forwarding number.
- [ ] **Authenticate the domain in Brevo.** Sending from a `@gmail.com`
      address triggers DKIM/DMARC warnings and risks the spam folder. Adding
      DNS records for `24hoursfacilitymaintenance.com` and sending from
      `noreply@` clears both.
- [ ] **`/privacy/` returns 404.** The cookie banner links to it from every
      page (`base.html:298`) but no route exists.
- [ ] **The cookie banner is cosmetic.** Accept and Decline only set a
      localStorage flag; neither gates any tracking.
- [ ] **Enhanced conversions.** The form already collects name, email and
      phone. Sending them hashed typically recovers 5–15% of conversions lost
      to cookie restrictions. Requires a privacy policy first.
- [ ] Reply to the DigitalOcean SMTP ticket if plain SMTP is still wanted.

---

## Key Lessons

**GTM is not the Google tag.** A container can be installed and firing while
carrying no tags at all. It looks correct in the page source and reports
nothing.

**A CSP can silently break tracking.** No error surfaces in the UI, tags appear
installed, and conversions read zero. Any new third-party script needs its
hosts added to `janitorial_site/middleware.py`.

**GA4-imported conversion actions have no label.** Only actions created as
Website → Manual event produce an event snippet that code can fire.

**Lead capture deserves tests.** The form was broken for weeks while looking
perfectly normal to anyone glancing at the page. `core/tests.py` now covers
that path so a silent break fails the build instead of the business.
