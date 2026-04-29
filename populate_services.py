import os
import django
from django.utils.text import slugify

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'janitorial_site.settings')
django.setup()

from core.models import Service

def populate():
    print("Deleting old generic services...")
    Service.objects.all().delete()

    services_data = [
        "Commercial Cleaning Services",
        "Janitorial Services",
        "Professional Floor Care & Restoration",
        "Property Turnover Cleaning & Maintenance",
        "Carpet & Upholstery Cleaning",
        "Industrial Pressure Washing",
        "Exterior Building Soft Wash",
        "Roof Washing",
        "Window Washing",
        "Temp Janitorial Staffing",
        "Runner Service",
        "Desk Clerk Service",
        "Temp Desk Clerk Services",
        "Hauling Services",
        "Minor Maintenance Service",
        "Daily Disinfection Specialist",
        "Commercial Kitchen Cleaning",
        "Construction Cleaning",
        "Industrial Cleaning",
        "Hardwood Floor Cleaning & Restoration"
    ]

    icons = [
        "fas fa-building", "fas fa-broom", "fas fa-fan", "fas fa-home", 
        "fas fa-couch", "fas fa-water", "fas fa-spray-can", "fas fa-home", 
        "fas fa-window-maximize", "fas fa-users", "fas fa-running", "fas fa-user-tie", 
        "fas fa-user-tie", "fas fa-truck", "fas fa-tools", "fas fa-shield-virus", 
        "fas fa-utensils", "fas fa-hard-hat", "fas fa-industry", "fas fa-tree"
    ]

    print(f"Adding {len(services_data)} new specific services...")
    
    for i, title in enumerate(services_data):
        icon = icons[i] if i < len(icons) else "fas fa-check-circle"
        
        Service.objects.create(
            title=title,
            slug=slugify(title),
            description=f"Professional {title.lower()} tailored to the unique needs of your facility, ensuring safety, cleanliness, and operational efficiency.",
            detailed_content=f"<p>Our <strong>{title}</strong> is designed to meet the rigorous demands of modern facilities. At 24 Hours Facility Maintenance Inc., our expert team uses industry-leading practices and advanced equipment to deliver outstanding results.</p><p>We understand that facility needs don't keep office hours, which is why we are available 24/7. Contact us today to learn how our {title.lower()} can improve your workspace.</p>",
            meta_title=f"{title} | 24 Hours Facility Maintenance Inc.",
            meta_description=f"Expert {title.lower()} by 24 Hours Facility Maintenance Inc. Reliable, professional, and available 24/7 across California.",
            icon_class=icon,
            is_active=True,
            order=i
        )
    
    print("Database successfully populated with 20 client services!")

if __name__ == '__main__':
    populate()
