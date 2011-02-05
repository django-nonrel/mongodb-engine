DATABASES = {
    'default' : {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'test',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '27017',
        'SUPPORTS_TRANSACTIONS': False,
    },
}

INSTALLED_APPS = ['djangotoolbox', 'general', 'embedded', 'or_lookups',
                  'aggregations', 'contrib', 'search', 'storage']
