# """
# Django settings for tests project.
# """

import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = '+&l^d!%soa4gxsnx7_txbo0x3uv$@4i&n!r8yte72otwqo7vmh'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

OSCAR_DEFAULT_CURRENCY = 'EUR'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
)

INSTALLED_APPS = ('adyen',)
