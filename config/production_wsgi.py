"""Entrypoint production tường minh, không rơi về config.settings local."""
import os
from django.core.exceptions import ImproperlyConfigured
from django.core.wsgi import get_wsgi_application

if os.environ.get('DJANGO_SETTINGS_MODULE', 'config.production') != 'config.production':
    raise ImproperlyConfigured('Production WSGI yêu cầu DJANGO_SETTINGS_MODULE=config.production.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.production'
application = get_wsgi_application()
