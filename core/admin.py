from django.contrib import admin
from .models import Service, Testimonial, ServiceArea, Inquiry, SiteSetting

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    search_fields = ('title', 'description')

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'rating', 'is_featured', 'created_at')
    list_editable = ('is_featured',)
    list_filter = ('rating', 'is_featured')
    search_fields = ('name', 'text')

@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    list_display = ('city', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('city',)

@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'service_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'service_type')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('name', 'email', 'phone', 'service_type', 'message', 'created_at')

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Only allow 1 instance
        if SiteSetting.objects.exists():
            return False
        return True
