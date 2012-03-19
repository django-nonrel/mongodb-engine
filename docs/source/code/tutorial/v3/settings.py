DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'tutorial',
    }
},

INSTALLED_APPS = ['nonrelblog']

ROOT_URLCONF = 'urls'

DEBUG = TEMPLATE_DEBUG = True
