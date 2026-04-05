from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Service, Testimonial, ServiceArea, Inquiry, SiteSetting, Booking, JobApplication

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
        app = JobApplication(
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            position=request.POST.get('position'),
            resume_link=request.POST.get('resume_link', ''),
            cover_letter=request.POST.get('cover_letter', '')
        )
        app.save()
        messages.success(request, "Your application has been received! Our HR team will review it shortly.")
        return redirect('careers')
        
    return render(request, 'careers.html')

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
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        service_id = request.POST.get('service_id')
        preferred_date = request.POST.get('preferred_date')
        preferred_time = request.POST.get('preferred_time')
        notes = request.POST.get('notes')

        # Connect the selected service if provided
        service_instance = None
        if service_id:
            try:
                service_instance = Service.objects.get(id=service_id)
            except Service.DoesNotExist:
                pass

        Booking.objects.create(
            name=name,
            email=email,
            phone=phone,
            address=address,
            service=service_instance,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            notes=notes
        )
        
        # In a real scenario, we'd send an email here using django.core.mail.send_mail
        messages.success(request, "Your booking request has been submitted successfully. We will call you soon to confirm!")
        return redirect('contact')

    services = Service.objects.filter(is_active=True)
    return render(request, 'contact.html', {'services': services})

from django.http import HttpResponse

def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Disallow: /admin/",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
