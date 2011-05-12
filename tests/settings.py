DATABASES = {
    'default' : {
        'ENGINE': 'django_mongodb_engine',
        'NAME' : 'test'
    },
    'other' : {
        'ENGINE' : 'django_mongodb_engine',
        'NAME' : 'test2'
    }
}

INSTALLED_APPS = ['djangotoolbox', 'query', 'embedded', 'mongodb',
                  'aggregations', 'contrib', 'storage', 'django_mongodb_engine']

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
