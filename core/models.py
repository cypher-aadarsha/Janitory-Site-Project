from django.db import models

class Service(models.Model):
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True, blank=True, null=True, help_text="SEO-friendly URL identifier (auto-generated if left blank)")
    description = models.TextField(help_text="Short description for list views")
    detailed_content = models.TextField(blank=True, help_text="Full detailed content for the dedicated service page")
    meta_title = models.CharField(max_length=150, blank=True)
    meta_description = models.TextField(blank=True)
    icon_class = models.CharField(max_length=50, blank=True, help_text="CSS class for the icon (e.g., 'fas fa-broom')")
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    text = models.TextField()
    rating = models.IntegerField(default=5, help_text="Rating out of 5")
    is_featured = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.rating} Stars"


class ServiceArea(models.Model):
    city = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    description = models.TextField(blank=True, help_text="Short description")
    detailed_content = models.TextField(blank=True, help_text="Full content for the dedicated location page")
    meta_title = models.CharField(max_length=150, blank=True)
    meta_description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['city']

    def __str__(self):
        return self.city


class Inquiry(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    service_type = models.CharField(max_length=100, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Inquiries"
        ordering = ['-created_at']

    def __str__(self):
        return f"Inquiry from {self.name} - {self.service_type}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, related_name='bookings')
    address = models.TextField()
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    notes = models.TextField(blank=True, help_text="Any special instructions or details about the property.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # CRM Enhancements
    is_repeat_customer = models.BooleanField(default=False)
    lifetime_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # ─── Marketing attribution ───────────────────────────────────────────
    # Captured from the visitor's first landing page and carried in the
    # session until they submit. Without these, a lead in the CMS cannot be
    # traced back to the ad click that paid for it.
    gclid = models.CharField(
        max_length=255, blank=True,
        help_text="Google Ads click ID. Present when the lead came from a paid click."
    )
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=150, blank=True)
    utm_term = models.CharField(max_length=150, blank=True)
    landing_page = models.CharField(
        max_length=500, blank=True,
        help_text="First page of the visit that produced this lead."
    )
    referrer = models.CharField(max_length=500, blank=True)

    # ─── GA4 lead-lifecycle reporting ────────────────────────────────────
    # Captured client-side from the visitor's _ga cookie at submission time.
    # A staff status change happens later, from the CMS dashboard, with no
    # browser/gtag present -- this is the only thread tying that later event
    # back to the visitor's original GA4 session.
    ga_client_id = models.CharField(
        max_length=100, blank=True,
        help_text="GA4 client ID captured at submission. Needed to report qualify_lead/close_convert_lead server-side."
    )
    # Set once each event is attempted (sent or not) so a status that later
    # flaps back and forth (e.g. COMPLETED corrected back to CONFIRMED, then
    # marked COMPLETED again) cannot double-report the same conversion.
    qualify_lead_reported = models.BooleanField(default=False)
    close_convert_lead_reported = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-preferred_date', '-preferred_time']

    def __str__(self):
        return f"Booking Request from {self.name} for {self.service}"

    @property
    def is_paid_lead(self):
        """True when this lead can be attributed to a Google Ads click."""
        return bool(self.gclid) or self.utm_medium.lower() in ('cpc', 'ppc', 'paid')


class JobApplication(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    position = models.CharField(max_length=200)
    resume_link = models.URLField(help_text="Link to LinkedIn, Google Drive, or Portfolio", blank=True, null=True)
    cover_letter = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=[
        ('NEW', 'New'),
        ('REVIEWING', 'Reviewing'),
        ('INTERVIEWED', 'Interviewed'),
        ('REJECTED', 'Rejected'),
        ('HIRED', 'Hired')
    ], default='NEW')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.position} Application - {self.name}"


class SiteSetting(models.Model):
    site_name = models.CharField(max_length=200, default="24 Hours Facility Maintenance Inc.")
    contact_email = models.EmailField(default="24hrfacilitymaintenance@gmail.com")
    contact_phone = models.CharField(max_length=20, default="5109347490")
    address = models.CharField(max_length=250, default="601 Willow St. Unit G, Alameda CA 94501")
    whatsapp_number = models.CharField(max_length=20, blank=True, help_text="Include country code, e.g., 1234567890")
    google_review_link = models.URLField(blank=True, null=True, help_text="Link to your Google My Business review page")
    hero_title = models.CharField(max_length=200, default="Professional Cleaning Services in California")
    hero_subtitle = models.TextField(default="We provide top-notch commercial and residential cleaning.")
    # Social Links
    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)

    # Dynamic Stats Counters
    stat_years = models.IntegerField(default=25, help_text="Years in business")
    stat_clients = models.IntegerField(default=1500, help_text="Number of clients")
    stat_sqft = models.IntegerField(default=50, help_text="Millions of Sq Ft serviced")
    stat_retention = models.IntegerField(default=99, help_text="Client retention percentage")

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        # Ensure only one instance of SiteSettings exists
        if SiteSetting.objects.exists() and not self.pk:
            return
        return super().save(*args, **kwargs)

class GalleryImage(models.Model):
    title = models.CharField(max_length=150)
    before_image = models.ImageField(upload_to='gallery/')
    after_image = models.ImageField(upload_to='gallery/')
    description = models.TextField(blank=True, help_text="Short description of the cleaning transformation")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
