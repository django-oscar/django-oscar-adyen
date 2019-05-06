# """
# Django settings for tests project.
# """

import os

from oscar import get_core_apps
from oscar.defaults import *

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = '+&l^d!%soa4gxsnx7_txbo0x3uv$@4i&n!r8yte72otwqo7vmh'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

OSCAR_DEFAULT_CURRENCY = 'EUR'
OSCAR_REQUIRED_ADDRESS_FIELDS = []
OSCAR_SLUG_ALLOW_UNICODE = False

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
)

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'django.contrib.flatpages',

    'adyen',
] + get_core_apps()

ADYEN_IDENTIFIER = 'OscaroFR'
ADYEN_SECRET_KEY = 'oscaroscaroscaro'
ADYEN_ACTION_URL = 'https://test.adyen.com/hpp/select.shtml'
ADYEN_SKIN_CODE = 'cqQJKZpg'

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
}
