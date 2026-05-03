from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Service, Testimonial, ServiceArea, Inquiry, SiteSetting, Booking, JobApplication
from .forms import BookingForm, JobApplicationForm

def home(request):
    services = Service.objects.filter(is_active=True)[:3]
    featured_testimonials = Testimonial.objects.filter(is_featured=True)[:3]
    areas = ServiceArea.objects.filter(is_active=True)[:6]
    return render(request, 'home.html', {
        'services': services,
        'testimonials': featured_testimonials,
        'areas': areas
    })

def about(request):
    return render(request, 'about.html')

def quality(request):
    return render(request, 'quality.html')

def sustainability(request):
    return render(request, 'sustainability.html')

def careers(request):
    if request.method == 'POST':
        form = JobApplicationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your application has been received! Our HR team will review it shortly.")
            return redirect('careers')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = JobApplicationForm()
        
    return render(request, 'careers.html', {'form': form})

def news(request):
    return render(request, 'news.html')

def gallery_page(request):
    from .models import GalleryImage
    galleries = GalleryImage.objects.all().order_by('-created_at')
    return render(request, 'gallery.html', {'galleries': galleries})

def services_page(request):
    services = Service.objects.filter(is_active=True)
    return render(request, 'services.html', {'services': services})

from django.shortcuts import get_object_or_404

def service_detail(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    return render(request, 'service_detail.html', {'service': service})

def service_areas(request):
    areas = ServiceArea.objects.filter(is_active=True)
    return render(request, 'service_areas.html', {'areas': areas})

def service_area_detail(request, slug):
    area = get_object_or_404(ServiceArea, slug=slug, is_active=True)
    return render(request, 'service_area_detail.html', {'area': area})

def testimonials_page(request):
    testimonials = Testimonial.objects.all()
    return render(request, 'testimonials.html', {'testimonials': testimonials})

def contact(request):
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your booking request has been submitted successfully. We will call you soon to confirm!")
            return redirect('contact')
        else:
            messages.error(request, "Please correct the errors below and try again.")
    else:
        form = BookingForm()

    services = Service.objects.filter(is_active=True)
    return render(request, 'contact.html', {'services': services, 'form': form})

from django.http import HttpResponse

def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Disallow: /admin/",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
