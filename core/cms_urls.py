from django.urls import path
from . import cms_views

urlpatterns = [
    path('', cms_views.dashboard_home, name='cms_dashboard'),
    
    # Services
    path('services/', cms_views.cms_services, name='cms_services'),
    path('services/add/', cms_views.cms_service_edit, name='cms_service_add'),
    path('services/<int:pk>/edit/', cms_views.cms_service_edit, name='cms_service_edit'),
    path('services/<int:pk>/delete/', cms_views.cms_service_delete, name='cms_service_delete'),
    
    # Service Areas
    path('service-areas/', cms_views.cms_service_areas, name='cms_service_areas'),
    path('service-areas/add/', cms_views.cms_service_area_edit, name='cms_service_area_add'),
    path('service-areas/<int:pk>/edit/', cms_views.cms_service_area_edit, name='cms_service_area_edit'),
    path('service-areas/<int:pk>/delete/', cms_views.cms_service_area_delete, name='cms_service_area_delete'),
    
    # Testimonials
    path('testimonials/', cms_views.cms_testimonials, name='cms_testimonials'),
    path('testimonials/add/', cms_views.cms_testimonial_edit, name='cms_testimonial_add'),
    path('testimonials/<int:pk>/edit/', cms_views.cms_testimonial_edit, name='cms_testimonial_edit'),
    path('testimonials/<int:pk>/delete/', cms_views.cms_testimonial_delete, name='cms_testimonial_delete'),
    
    # Inquiries
    path('inquiries/', cms_views.cms_inquiries, name='cms_inquiries'),
    path('inquiries/<int:pk>/', cms_views.cms_inquiry_view, name='cms_inquiry_view'),
    path('inquiries/<int:pk>/delete/', cms_views.cms_inquiry_delete, name='cms_inquiry_delete'),
    
    # Site Settings
    path('settings/', cms_views.cms_site_settings, name='cms_site_settings'),
    
    # Bookings (CRM)
    path('bookings/', cms_views.cms_bookings, name='cms_bookings'),
    path('bookings/<int:pk>/', cms_views.cms_booking_view, name='cms_booking_view'),
    path('bookings/<int:pk>/delete/', cms_views.cms_booking_delete, name='cms_booking_delete'),
    
    # Job Applications (Careers)
    path('job-applications/', cms_views.cms_job_applications, name='cms_job_applications'),
    path('job-applications/<int:pk>/', cms_views.cms_job_application_view, name='cms_job_application_view'),
    path('job-applications/<int:pk>/delete/', cms_views.cms_job_application_delete, name='cms_job_application_delete'),
    
    # Gallery Before/After
    path('galleries/', cms_views.cms_galleries, name='cms_galleries'),
    path('galleries/add/', cms_views.cms_gallery_edit, name='cms_gallery_add'),
    path('galleries/<int:pk>/edit/', cms_views.cms_gallery_edit, name='cms_gallery_edit'),
    path('galleries/<int:pk>/delete/', cms_views.cms_gallery_delete, name='cms_gallery_delete'),
]
