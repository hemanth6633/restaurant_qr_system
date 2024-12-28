import os
from django.core.wsgi import get_wsgi_application
from django.core.management import execute_from_command_line

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_project.settings')

# Initialize Django
application = get_wsgi_application()

# Handler for Vercel
def handler(request):
    return application(request)
