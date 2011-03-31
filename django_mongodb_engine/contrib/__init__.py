from django.db import models, connections
from django.db.models.query import QuerySet
from django.db.models.sql import AND
from django.db.models.sql.query import Query as SQLQuery
from .mapreduce import MapReduceMixin

def _compiler_for_queryset(qs, which='SQLCompiler'):
    connection = connections[qs.db]
    Compiler = connection.ops.compiler(which)
    return Compiler(qs.query, connection, connection.alias)

class RawQuery(SQLQuery):
    def __init__(self, model, raw_query):
        super(RawQuery, self).__init__(model)
        self.raw_query = raw_query

    def clone(self, *args, **kwargs):
        clone = super(RawQuery, self).clone(*args, **kwargs)
        clone.raw_query = self.raw_query
        return clone

class RawQueryMixin:
    def get_raw_query_set(self, raw_query):
        return QuerySet(self.model, RawQuery(self.model, raw_query), self._db)

    def raw_query(self, query=None):
        """
        Does a raw MongoDB query. The optional parameter `query` is the spec
        passed to PyMongo's :meth:`~pymongo.Collection.find` method.
        """
        return self.get_raw_query_set(query or {})

    def raw_update(self, spec_or_q, update_dict, **kwargs):
        """
        Does a raw MongoDB update. `spec_or_q` is either a MongoDB filter
        dict or a :class:`~django.db.models.query_utils.Q` instance that selects
        the records to update. `update_dict` is a MongoDB style update document
        containing either a new document or atomic modifiers such as ``$inc``.

        Keyword arguments will be passed to :meth:`pymongo.Collection.update`.
        """
        if isinstance(spec_or_q, dict):
            queryset = self.get_raw_query_set(spec_or_q)
        else:
            queryset = self.filter(spec_or_q)
        queryset._for_write = True
        compiler = _compiler_for_queryset(queryset, 'SQLUpdateCompiler')
        compiler.execute_raw(update_dict, **kwargs)

    raw_update.alters_data = True

class MongoDBManager(models.Manager, MapReduceMixin, RawQueryMixin):
    """
    Example usage::

        from django_mongodb_engine.contrib import MongoDBManager

        class MyModel(models.Model):
            objects = MongoDBManager()

        MyModel.objects.map_reduce(...) # See `MapReduceMixin` documentation
        MyModel.objects.raw_query(...)  # See `RawQueryMixin` documentation
    """
