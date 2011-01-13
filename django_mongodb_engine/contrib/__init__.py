from django.db import models
from django.db.models.sql import AND
from mapreduce import MapReduceMixin

class RawQuery:
    def __init__(self, query):
        self.query = query

class RawSpec:
    def __init__(self, spec, kwargs):
        self.spec, self.kwargs = spec, kwargs

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

    def raw_update(self, spec_or_q, update_dict, **kwargs):
        """
        Does a raw MongoDB update. `spec_or_q` is either a MongoDB filter
        dict or a :class:`~django.db.models.query_utils.Q` instance that selects
        the records to update. `update_dict` is a MongoDB style update document
        containing either a new document or atomic modifiers such as ``$inc``.

        Keyword arguments will be passed to :meth:`pymongo.Collection.update`.
        """
        queryset = self.get_query_set()
        if isinstance(spec_or_q, dict):
            queryset.query.where.add(RawQuery(spec_or_q), AND)
        else:
            queryset = queryset.filter(spec_or_q)
        dummy_field = self.model._meta.pk.column
        return queryset.update(**{dummy_field: RawSpec(update_dict, kwargs)})

class MongoDBManager(models.Manager, MapReduceMixin, RawQueryMixin):
    """
    Example usage::

        from django_mongodb_engine.contrib import MongoDBManager

        class MyModel(models.Model):
            objects = MongoDBManager()

        MyModel.objects.map_reduce(...) # See `MapReduceMixin` documentation
        MyModel.objects.raw_query(...)  # See `RawQueryMixin` documentation
    """
