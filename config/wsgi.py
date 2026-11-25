import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

application = get_wsgi_application()
app = application

from apps.core.firebase_admin_helper import init_firebase_admin
init_firebase_admin()
