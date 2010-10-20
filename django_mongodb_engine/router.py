from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

def model_label(model):
    return '%s.%s' % (model._meta.app_label, model._meta.module_name)

class MongoDBRouter(object):
    """
    A router to control all database operations on models in the myapp application
    """
    def __init__(self):
        self.managed_apps = [app.split('.')[-1] for app in getattr(settings, 'MONGODB_MANAGED_APPS', [])]
        self.managed_models = getattr(settings, 'MONGODB_MANAGED_MODELS', [])
        self.mongodb_database, self.mongodb_databases = self.get_databases()

    def get_databases(self):
        default_database = None
        databases = []
        for name, databaseopt in settings.DATABASES.iteritems():
            if databaseopt['ENGINE'] == 'django_mongodb_engine':
                databases.append(name)
                if databaseopt.get('IS_DEFAULT'):
                    if default_database is None:
                        default_database = name
                    else:
                        raise ImproperlyConfigured("There an be only one default MongoDB database")

        if not databases:
            raise ImproperlyConfigured("No MongoDB database found in settings.DATABASES")

        if default_database is None:
            default_database = databases[0]

        return default_database, databases

    def model_app_is_managed(self, model):
        return model._meta.app_label in self.managed_apps

    def model_is_managed(self, model):
        return model_label(model) in self.managed_models

    def is_managed(self, model):
        return self.model_app_is_managed(model) or self.model_is_managed(model)

    def db_for_read(self, model, **hints):
        """Point all operations on mongodb models to a mongodb database"""
        if self.is_managed(model):
            return self.mongodb_database

    db_for_write = db_for_read # same algorithm

    def allow_relation(self, obj1, obj2, **hints):
        """Allow any relation if a model in myapp is involved"""
        return self.is_managed(obj2) or None

    def allow_syncdb(self, db, model):
        """Make sure that a mongodb model appears on a mongodb database"""

        if db in self.mongodb_databases:
           return self.is_managed(model)
        elif self.is_managed(model):
            return db in self.mongodb_databases
            
        return None 

    def valid_for_db_engine(self, driver, model):
        """Make sure that a model is valid for a database provider"""
        if driver != 'mongodb':
            return False
        return self.is_managed(model)
