from settings import *


DATABASES = {
    'default': {
        'NAME': 'test',
        'ENGINE': 'sqlite3',
    },
}
for app in ['embedded', 'storage']:
    INSTALLED_APPS.remove(app)

DATABASES['mongodb'] = {'NAME': 'mongodb', 'ENGINE': 'django_mongodb_engine'}
