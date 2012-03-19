from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


_mongodbs = []

def _init_mongodbs():
    for name, options in settings.DATABASES.iteritems():
        if options['ENGINE'] != 'django_mongodb_engine':
            continue
        if options.get('IS_DEFAULT'):
            _mongodbs.insert(0, name)
        else:
            _mongodbs.append(name)

    if not _mongodbs:
        raise ImproperlyConfigured("No MongoDB database found in "
                                   "settings.DATABASES.")


class MongoDBRouter(object):
    """
    A Django router to manage models that should be stored in MongoDB.

    MongoDBRouter uses the MONGODB_MANAGED_APPS and MONGODB_MANAGED_MODELS
    settings to know which models/apps should be stored inside MongoDB.

    See: http://docs.djangoproject.com/en/dev/topics/db/multi-db/#topics-db-multi-db-routing
    """

    def __init__(self):
        if not _mongodbs:
            _init_mongodbs()
        self.managed_apps = [app.split('.')[-1] for app in
                             getattr(settings, 'MONGODB_MANAGED_APPS', [])]
        self.managed_models = getattr(settings, 'MONGODB_MANAGED_MODELS', [])

    def is_managed(self, model):
        """
        Returns True if the model passed is managed by Django MongoDB
        Engine.
        """
        if model._meta.app_label in self.managed_apps:
            return True
        full_name = '%s.%s' % (model._meta.app_label, model._meta.object_name)
        return full_name in self.managed_models

    def db_for_read(self, model, **hints):
        """
        Points all operations on MongoDB models to a MongoDB database.
        """
        if self.is_managed(model):
            return _mongodbs[0]

    db_for_write = db_for_read # Same algorithm.

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allows any relation if a model in myapp is involved.
        """
        return self.is_managed(obj2) or None

    def allow_syncdb(self, db, model):
        """
        Makes sure that MongoDB models only appear on MongoDB databases.
        """
        if db in _mongodbs:
            return self.is_managed(model)
        elif self.is_managed(model):
            return db in _mongodbs
        return None
