from settings import *


INSTALLED_APPS = ['query', 'router']

DATABASES['default'] = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': '/tmp/db.sql'}

DATABASE_ROUTERS = ['django_mongodb_engine.router.MongoDBRouter']
MONGODB_MANAGED_APPS = ['query']
MONGODB_MANAGED_MODELS = ['router.MongoDBModel']
