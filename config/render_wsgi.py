"""Entrypoint riêng Render, không thể rơi về SQLite/local."""
import os
from django.core.exceptions import ImproperlyConfigured
from django.core.wsgi import get_wsgi_application

if os.environ.get('DJANGO_SETTINGS_MODULE') != 'config.render' or os.environ.get('RENDER') != 'true':
    raise ImproperlyConfigured('Render WSGI yêu cầu config.render và RENDER=true.')
application = get_wsgi_application()
