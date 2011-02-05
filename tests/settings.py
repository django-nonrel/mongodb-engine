# Run the test for 'general' with this setting on and off
MONGODB_AUTOMATIC_REFERENCING = True

DATABASES = {
    'default': {
        'ENGINE' : 'dbindexer',
        'TARGET' : 'mongodb'
    },
    'mongodb' : {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'test',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '27017',
        'SUPPORTS_TRANSACTIONS': False,
    },
}

INSTALLED_APPS = ['dbindexer', 'djangotoolbox', 'general', 'embedded',
                  'or_lookups', 'aggregations', 'contrib', 'search', 'storage']

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
    for app in ['embedded', 'search', 'storage']:
        INSTALLED_APPS.remove(app)

ROOT_URLCONF = ''
DBINDEXER_SITECONF = 'dbindexes'
