"""
Django Forms for input validation and sanitization.
Replaces raw request.POST.get() usage across all views.
"""
from django import forms
from .models import (
    Service, Testimonial, ServiceArea, Inquiry,
    SiteSetting, Booking, JobApplication, GalleryImage
)


# ─── Public-facing Forms ─────────────────────────────────────────────────

class BookingForm(forms.ModelForm):
    """Validates the contact/booking form submitted by site visitors."""
    class Meta:
        model = Booking
        fields = [
            'name', 'email', 'phone', 'address',
            'service', 'preferred_date', 'preferred_time', 'notes'
        ]
        widgets = {
            'preferred_date': forms.DateInput(attrs={'type': 'date'}),
            'preferred_time': forms.TimeInput(attrs={'type': 'time'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter a valid name.")
        return name

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError("Email is required.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if len(phone) < 7:
            raise forms.ValidationError("Please enter a valid phone number.")
        return phone


class JobApplicationForm(forms.ModelForm):
    """Validates the careers application form."""
    class Meta:
        model = JobApplication
        fields = ['name', 'email', 'phone', 'position', 'resume_link', 'cover_letter']

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter a valid name.")
        return name


# ─── CMS Admin Forms ─────────────────────────────────────────────────────

class ServiceForm(forms.ModelForm):
    """Validates CMS service creation/editing."""
    class Meta:
        model = Service
        fields = [
            'title', 'slug', 'description', 'detailed_content',
            'meta_title', 'meta_description', 'icon_class',
            'image', 'order', 'is_active'
        ]

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Service title is required.")
        if len(title) > 150:
            raise forms.ValidationError("Title must be 150 characters or fewer.")
        return title

    def clean_order(self):
        order = self.cleaned_data.get('order')
        if order is None:
            return 0
        return order


class ServiceAreaForm(forms.ModelForm):
    """Validates CMS service area creation/editing."""
    class Meta:
        model = ServiceArea
        fields = [
            'city', 'slug', 'description', 'detailed_content',
            'meta_title', 'meta_description', 'is_active'
        ]

    def clean_city(self):
        city = self.cleaned_data.get('city', '').strip()
        if not city:
            raise forms.ValidationError("City name is required.")
        return city


class TestimonialForm(forms.ModelForm):
    """Validates CMS testimonial creation/editing."""
    class Meta:
        model = Testimonial
        fields = ['name', 'text', 'rating', 'is_featured']

    def clean_rating(self):
        rating = self.cleaned_data.get('rating', 5)
        if not (1 <= rating <= 5):
            raise forms.ValidationError("Rating must be between 1 and 5.")
        return rating


class SiteSettingForm(forms.ModelForm):
    """Validates CMS site settings."""
    class Meta:
        model = SiteSetting
        fields = [
            'site_name', 'contact_email', 'contact_phone', 'address',
            'whatsapp_number', 'hero_title', 'hero_subtitle',
            'google_review_link', 'facebook_url', 'instagram_url',
            'stat_years', 'stat_clients', 'stat_sqft', 'stat_retention'
        ]

    def clean_contact_email(self):
        email = self.cleaned_data.get('contact_email', '').strip()
        if not email:
            raise forms.ValidationError("Contact email is required.")
        return email


class GalleryImageForm(forms.ModelForm):
    """Validates CMS gallery image creation/editing."""
    class Meta:
        model = GalleryImage
        fields = ['title', 'description', 'before_image', 'after_image']

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Gallery title is required.")
        return title
