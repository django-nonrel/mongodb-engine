from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from django_mongodb_engine.utils import get_databases

def model_label(model):
    return '%s.%s' % (model._meta.app_label, model._meta.module_name)

class MongoDBRouter(object):
    """
    A router to control all database operations on models in the myapp application
    """
    def __init__(self):
        self.managed_apps = [app.split('.')[-1] for app in getattr(settings, 'MONGODB_MANAGED_APPS', [])]
        self.managed_models = getattr(settings, 'MONGODB_MANAGED_MODELS', [])
        self.mongodb_database, self.mongodb_databases = get_databases()

    def model_app_is_managed(self, model):
        return model._meta.app_label in self.managed_apps

    def model_is_managed(self, model):
        return model_label(model) in self.managed_models

    def is_managed(self, model):
        # Extra check to prevent errors
        # the import has to be placed here
        # to prevent connections errors
        from django.db.models import Model
        if not isinstance(model, Model) and not issubclass(model, Model):
            return None
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
