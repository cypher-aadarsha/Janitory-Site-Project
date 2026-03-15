from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Service, Testimonial, ServiceArea, Inquiry, SiteSetting

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

def services_page(request):
    services = Service.objects.filter(is_active=True)
    return render(request, 'services.html', {'services': services})

def service_areas(request):
    areas = ServiceArea.objects.filter(is_active=True)
    return render(request, 'service_areas.html', {'areas': areas})

def testimonials_page(request):
    testimonials = Testimonial.objects.all()
    return render(request, 'testimonials.html', {'testimonials': testimonials})

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        service_type = request.POST.get('service_type')
        message = request.POST.get('message')

        Inquiry.objects.create(
            name=name,
            email=email,
            phone=phone,
            service_type=service_type,
            message=message
        )
        
        # In a real scenario, we'd send an email here using django.core.mail.send_mail
        messages.success(request, "Your inquiry has been submitted successfully. We will contact you soon!")
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
