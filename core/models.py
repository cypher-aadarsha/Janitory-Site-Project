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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-preferred_date', '-preferred_time']

    def __str__(self):
        return f"{self.name} - {self.preferred_date} at {self.preferred_time}"


class SiteSetting(models.Model):
    site_name = models.CharField(max_length=100, default="Cleaning Services")
    contact_email = models.EmailField(default="info@cleaningservice.com")
    contact_phone = models.CharField(max_length=20, default="123-456-7890")
    address = models.TextField(default="California, USA")
    whatsapp_number = models.CharField(max_length=20, blank=True, help_text="Include country code, e.g., 1234567890")
    hero_title = models.CharField(max_length=200, default="Professional Cleaning Services in California")
    hero_subtitle = models.TextField(default="We provide top-notch commercial and residential cleaning.")
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)

    def __str__(self):
        return "Site Settings"

    def save(self, *args, **kwargs):
        # Ensure only one instance of SiteSettings exists
        if SiteSetting.objects.exists() and not self.pk:
            return
        return super().save(*args, **kwargs)
