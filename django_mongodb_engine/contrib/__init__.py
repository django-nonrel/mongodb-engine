from django.db import models
from mapreduce import MapReduceMixin

class MongoDBManager(models.Manager, MapReduceMixin):
    """
    Example usage::

        from django_mongodb_engine.contrib import MongoDBManager
        class MyModel(models.Model):
            objects = MongoDBManager()

        MyModel.objects.map_reduce(...) # See `MapReduceMixin` documentation
    """
