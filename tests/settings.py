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

# 

INSTALLED_APPS = 'aggregations contrib embedded general or_lookups search storage'.split()

# shortcut to check whether tests would pass using an SQL backend
USE_SQLITE = False
# USE_SQLITE = True

if USE_SQLITE:
    DATABASES = {
            'default' : {
                    'NAME' : 'test',
                    'ENGINE' : 'sqlite3',
                    }
                }
    INSTALLED_APPS.remove('embedded')
    INSTALLED_APPS.remove('search')
