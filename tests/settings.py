# Run the test for 'myapp' with this setting on and off
MONGODB_AUTOMATIC_REFERENCING = True

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

# aggregations contrib embedded general or_lookups storage 

INSTALLED_APPS = 'search'.split()

# shortcut to check whether tests would pass using an SQL backend
USE_SQLITE = False

if USE_SQLITE:
    DATABASES = {'default' : {'ENGINE' : 'sqlite3'}}
    INSTALLED_APPS.remove('embedded')
