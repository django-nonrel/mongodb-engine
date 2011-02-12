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
                  'aggregations', 'contrib', 'storage']

LOGGING = {
    'version' : 1,
    'formatters' : {'simple' : {'format': '%(levelname)s %(message)s'}},
    'handlers' : {
        'console' : {
            'level' : 'DEBUG',
            'class' : 'logging.StreamHandler',
            'formatter' : 'simple'
        }
    },
    'loggers' : {
        'django.db.backends' : {
            'level' : 'DEBUG',
            'handlers' : ['console']
        }
    }
}
