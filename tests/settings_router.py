from settings import *

INSTALLED_APPS = ['general', 'router']

DATABASES['default'] = {'ENGINE' : 'sqlite3', 'NAME' : '/tmp/db.sql'}

DATABASE_ROUTERS = ['django_mongodb_engine.router.MongoDBRouter']
MONGODB_MANAGED_APPS = ['general']
MONGODB_MANAGED_MODELS = ['router.MongoDBModel']
