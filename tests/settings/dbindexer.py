from settings import *


DATABASES['mongodb'] = DATABASES['default']
DATABASES['default'] = {'ENGINE': 'dbindexer', 'TARGET': 'mongodb'}

ROOT_URLCONF = ''
DBINDEXER_SITECONF = 'dbindexes'

INSTALLED_APPS = INSTALLED_APPS + ['dbindexer']
