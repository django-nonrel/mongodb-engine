DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'tutorial',
    },
}

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',

    'nonrelblog',
]

ROOT_URLCONF = 'urls'

DEBUG = TEMPLATE_DEBUG = True
