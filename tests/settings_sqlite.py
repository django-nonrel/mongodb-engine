from settings import *

DATABASES = {
    'default' : {
        'NAME' : 'test',
        'ENGINE' : 'sqlite3',
    }
}
for app in ['embedded', 'search', 'storage']:
    INSTALLED_APPS.remove(app)
