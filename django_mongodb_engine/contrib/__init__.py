from django.db import models
from django.db.models.sql import AND
from mapreduce import MapReduceMixin

class RawQuery:
    def __init__(self, query):
        self.query = query

class RawQueryMixin:
    def raw_query(self, query=None):
        """
        Does a raw MongoDB query. The optional parameter `query` is the spec
        passed to PyMongo's :meth:`~pymongo.Collection.find` method.

        Note that you can't use regular Django filters and :meth:`raw_query`
        at the same time. Trying to do so will raise a :exc:`TypeError`.
        """
        if query is None:
            query = {}
        queryset = self.get_query_set()
        queryset.query.where.add(RawQuery(query), AND)
        return queryset

class MongoDBManager(models.Manager, MapReduceMixin, RawQueryMixin):
    """
    Example usage::

        from django_mongodb_engine.contrib import MongoDBManager

        class MyModel(models.Model):
            objects = MongoDBManager()

        MyModel.objects.map_reduce(...) # See `MapReduceMixin` documentation
        MyModel.objects.raw_query(...)  # See `RawQueryMixin` documentation
    """
