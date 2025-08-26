import os
import sys
from django.core.wsgi import get_wsgi_application

# Add the project directory to the sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = get_wsgi_application()