from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.text import slugify
from .models import Service, Testimonial, ServiceArea, Inquiry, SiteSetting, Booking, JobApplication

def is_staff_or_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def dashboard_home(request):
    total_services = Service.objects.count()
    total_inquiries = Inquiry.objects.count()
    total_bookings = Booking.objects.count()
    total_applications = JobApplication.objects.count()
    
    # Recent activity
    recent_inquiries = Inquiry.objects.all().order_by('-created_at')[:5]
    recent_bookings = Booking.objects.all().order_by('-created_at')[:5]
    
    # Aggregations for charts
    from django.db.models import Count
    bookings_by_status = list(Booking.objects.values('status').annotate(count=Count('id')))
    apps_by_status = list(JobApplication.objects.values('status').annotate(count=Count('id')))
    
    import json
    context = {
        'total_services': total_services,
        'total_inquiries': total_inquiries,
        'total_bookings': total_bookings,
        'total_applications': total_applications,
        'recent_inquiries': recent_inquiries,
        'recent_bookings': recent_bookings,
        'bookings_by_status_json': json.dumps(bookings_by_status),
        'apps_by_status_json': json.dumps(apps_by_status),
    }
    return render(request, 'cms/dashboard.html', context)

# --- Service Management ---
@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_services(request):
    services = Service.objects.all().order_by('order')
    return render(request, 'cms/service_list.html', {'services': services})

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_service_edit(request, pk=None):
    if pk:
        service = get_object_or_404(Service, pk=pk)
        action = "Edit"
    else:
        service = Service()
        action = "Add"
        
    if request.method == 'POST':
        service.title = request.POST.get('title')
        service.description = request.POST.get('description')
        service.detailed_content = request.POST.get('detailed_content', '')
        service.meta_title = request.POST.get('meta_title', '')
        service.meta_description = request.POST.get('meta_description', '')
        
        # Auto-generate slug if empty
        slug = request.POST.get('slug', '')
        if not slug and service.title:
            service.slug = slugify(service.title)
        else:
            service.slug = slugify(slug)
            
        service.icon_class = request.POST.get('icon_class', '')
        service.order = request.POST.get('order') or 0
        service.is_active = request.POST.get('is_active') == 'on'
        
        if 'image' in request.FILES:
            service.image = request.FILES['image']
            
        service.save()
        messages.success(request, f"Service '{service.title}' has been successfully saved.")
        return redirect('cms_services')
        
    return render(request, 'cms/service_form.html', {'service': service, 'action': action})

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        title = service.title
        service.delete()
        messages.success(request, f"Service '{title}' has been deleted.")
        return redirect('cms_services')
    return render(request, 'cms/confirm_delete.html', {'object': service, 'cancel_url': 'cms_services'})

# --- Service Area Management ---
@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_service_areas(request):
    areas = ServiceArea.objects.all()
    return render(request, 'cms/service_area_list.html', {'areas': areas})

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_service_area_edit(request, pk=None):
    if pk:
        area = get_object_or_404(ServiceArea, pk=pk)
        action = "Edit"
    else:
        area = ServiceArea()
        action = "Add"
        
    if request.method == 'POST':
        area.city = request.POST.get('city')
        area.description = request.POST.get('description', '')
        area.detailed_content = request.POST.get('detailed_content', '')
        area.meta_title = request.POST.get('meta_title', '')
        area.meta_description = request.POST.get('meta_description', '')
        
        # Auto-generate slug if empty
        slug = request.POST.get('slug', '')
        if not slug and area.city:
            area.slug = slugify(area.city)
        else:
            area.slug = slugify(slug)
            
        area.is_active = request.POST.get('is_active') == 'on'
        area.save()
        messages.success(request, f"Service Area '{area.city}' has been successfully saved.")
        return redirect('cms_service_areas')
        
    return render(request, 'cms/service_area_form.html', {'area': area, 'action': action})

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_service_area_delete(request, pk):
    area = get_object_or_404(ServiceArea, pk=pk)
    if request.method == 'POST':
        city = area.city
        area.delete()
        messages.success(request, f"Service Area '{city}' has been deleted.")
        return redirect('cms_service_areas')
    return render(request, 'cms/confirm_delete.html', {'object': area, 'cancel_url': 'cms_service_areas'})

# --- Testimonial Management ---
@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_testimonials(request):
    testimonials = Testimonial.objects.all().order_by('-created_at')
    return render(request, 'cms/testimonial_list.html', {'testimonials': testimonials})

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_testimonial_edit(request, pk=None):
    if pk:
        testimonial = get_object_or_404(Testimonial, pk=pk)
        action = "Edit"
    else:
        testimonial = Testimonial()
        action = "Add"
        
    if request.method == 'POST':
        testimonial.client_name = request.POST.get('client_name')
        testimonial.review_text = request.POST.get('review_text')
        testimonial.rating = request.POST.get('rating') or 5
        testimonial.is_featured = request.POST.get('is_featured') == 'on'
        testimonial.save()
        messages.success(request, f"Testimonial from '{testimonial.client_name}' has been successfully saved.")
        return redirect('cms_testimonials')
        
    return render(request, 'cms/testimonial_form.html', {'testimonial': testimonial, 'action': action})

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_testimonial_delete(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk)
    if request.method == 'POST':
        name = testimonial.client_name
        testimonial.delete()
        messages.success(request, f"Testimonial from '{name}' has been deleted.")
        return redirect('cms_testimonials')
    return render(request, 'cms/confirm_delete.html', {'object': testimonial, 'cancel_url': 'cms_testimonials'})

# --- Inquiry Management ---
@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_inquiries(request):
    inquiries = Inquiry.objects.all().order_by('-created_at')
    return render(request, 'cms/inquiry_list.html', {'inquiries': inquiries})

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_inquiry_view(request, pk):
    inquiry = get_object_or_404(Inquiry, pk=pk)
    return render(request, 'cms/inquiry_detail.html', {'inquiry': inquiry})

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_inquiry_delete(request, pk):
    inquiry = get_object_or_404(Inquiry, pk=pk)
    if request.method == 'POST':
        name = inquiry.name
        inquiry.delete()
        messages.success(request, f"Inquiry from '{name}' has been deleted.")
        return redirect('cms_inquiries')
    return render(request, 'cms/confirm_delete.html', {'object': inquiry, 'cancel_url': 'cms_inquiries'})

# --- Site Settings Management ---
@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_site_settings(request):
    settings_obj = SiteSetting.objects.first()
    if not settings_obj:
        settings_obj = SiteSetting()
        
    if request.method == 'POST':
        settings_obj.site_name = request.POST.get('site_name')
        settings_obj.contact_email = request.POST.get('contact_email')
        settings_obj.contact_phone = request.POST.get('contact_phone')
        settings_obj.address = request.POST.get('address')
        settings_obj.whatsapp_number = request.POST.get('whatsapp_number')
        settings_obj.hero_title = request.POST.get('hero_title', '')
        settings_obj.hero_subtitle = request.POST.get('hero_subtitle', '')
        settings_obj.google_review_link = request.POST.get('google_review_link', '')
        settings_obj.facebook_url = request.POST.get('facebook_url', '')
        settings_obj.instagram_url = request.POST.get('instagram_url', '')

        # Process dynamic stats counters (with fallback defaults if empty or invalid)
        try:
            settings_obj.stat_years = int(request.POST.get('stat_years', 25))
            settings_obj.stat_clients = int(request.POST.get('stat_clients', 1500))
            settings_obj.stat_sqft = int(request.POST.get('stat_sqft', 50))
            settings_obj.stat_retention = int(request.POST.get('stat_retention', 99))
        except ValueError:
            pass
        
        settings_obj.save()
        messages.success(request, "Global site settings have been updated successfully.")
        return redirect('cms_site_settings')
        
    return render(request, 'cms/site_settings_form.html', {'settings': settings_obj})

# --- Booking Management (CRM) ---
@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_bookings(request):
    # Optional filtering by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        bookings = Booking.objects.filter(status=status_filter)
    else:
        bookings = Booking.objects.all()
        
    return render(request, 'cms/booking_list.html', {
        'bookings': bookings,
        'current_filter': status_filter
    })

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_booking_view(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    
    # Grab the site settings to pass to context for the Google Review link
    site_settings = SiteSetting.objects.first()
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Booking.STATUS_CHOICES):
            booking.status = new_status
            
        booking.is_repeat_customer = request.POST.get('is_repeat_customer') == 'on'
        try:
            booking.lifetime_value = float(request.POST.get('lifetime_value', 0.00))
        except ValueError:
            pass
            
        booking.save()
        messages.success(request, f"CRM Profile for '{booking.name}' has been updated.")
        return redirect('cms_booking_view', pk=booking.pk)
            
    return render(request, 'cms/booking_detail.html', {'booking': booking, 'site_settings': site_settings})

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_booking_delete(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        name = booking.name
        booking.delete()
        messages.success(request, f"Booking for '{name}' has been deleted.")
        return redirect('cms_bookings')
    return render(request, 'cms/confirm_delete.html', {'object': booking, 'cancel_url': 'cms_bookings'})

# --- Job Applications Management (Careers) ---
@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_job_applications(request):
    status_filter = request.GET.get('status', '')
    if status_filter:
        applications = JobApplication.objects.filter(status=status_filter)
    else:
        applications = JobApplication.objects.all()
        
    return render(request, 'cms/job_application_list.html', {
        'applications': applications,
        'current_filter': status_filter
    })

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_job_application_view(request, pk):
    application = get_object_or_404(JobApplication, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(JobApplication.STATUS_CHOICES):
            application.status = new_status
            application.save()
            messages.success(request, f"Application status updated to {application.get_status_display()}.")
            return redirect('cms_job_application_view', pk=application.pk)
            
    return render(request, 'cms/job_application_detail.html', {'application': application})

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_job_application_delete(request, pk):
    application = get_object_or_404(JobApplication, pk=pk)
    if request.method == 'POST':
        name = application.name
        application.delete()
        messages.success(request, f"Application from '{name}' has been deleted.")
        return redirect('cms_job_applications')
    return render(request, 'cms/confirm_delete.html', {'object': application, 'cancel_url': 'cms_job_applications'})

# --- Gallery Management ---
@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_galleries(request):
    from .models import GalleryImage
    galleries = GalleryImage.objects.all().order_by('-created_at')
    return render(request, 'cms/gallery_list.html', {'galleries': galleries})

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_gallery_edit(request, pk=None):
    from .models import GalleryImage
    if pk:
        gallery = get_object_or_404(GalleryImage, pk=pk)
        action = "Edit"
    else:
        gallery = GalleryImage()
        action = "Add"
        
    if request.method == 'POST':
        gallery.title = request.POST.get('title')
        gallery.description = request.POST.get('description', '')
        
        if 'before_image' in request.FILES:
            gallery.before_image = request.FILES['before_image']
        if 'after_image' in request.FILES:
            gallery.after_image = request.FILES['after_image']
            
        gallery.save()
        messages.success(request, f"Gallery Image '{gallery.title}' has been successfully saved.")
        return redirect('cms_galleries')
        
    return render(request, 'cms/gallery_form.html', {'gallery': gallery, 'action': action})

@user_passes_test(is_staff_or_admin, login_url='/admin/login/')
def cms_gallery_delete(request, pk):
    from .models import GalleryImage
    gallery = get_object_or_404(GalleryImage, pk=pk)
    if request.method == 'POST':
        title = gallery.title
        gallery.delete()
        messages.success(request, f"Gallery Image '{title}' has been deleted.")
        return redirect('cms_galleries')
    return render(request, 'cms/confirm_delete.html', {'object': gallery, 'cancel_url': 'cms_galleries'})
