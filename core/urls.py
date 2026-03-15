from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services_page, name='services'),
    path('service-areas/', views.service_areas, name='service_areas'),
    path('testimonials/', views.testimonials_page, name='testimonials'),
    path('contact/', views.contact, name='contact'),
]
