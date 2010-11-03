DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'test',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '27017',
        'SUPPORTS_TRANSACTIONS': False,
    },
}

INSTALLED_APPS = 'aggregations contrib embedded myapp'.split()

if 0:
    # shortcut to check whether tests would pass using an SQL backend
    DATABASES = {'default' : {'ENGINE' : 'sqlite3'}}
    INSTALLED_APPS.remove('embedded')
    INSTALLED_APPS.remove('myapp')
