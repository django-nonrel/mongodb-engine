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

SERIALIZATION_MODULES = {'json' : 'settings.serializer'}
