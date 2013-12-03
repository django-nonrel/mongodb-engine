import sys

from django.db import models, connections, router
from django.db.models.query import QuerySet
from django.db.models.sql import Query as SQLQuery, UpdateQuery


ON_PYPY = hasattr(sys, 'pypy_version_info')


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
        passed to PyMongo's :meth:`<Collection.find> pymongo.Collection.find`.
        """
        return self.get_raw_query_set(query or {})

    def raw_update(self, spec_or_q, update_dict, **kwargs):
        """
        Does a raw MongoDB update. `spec_or_q` is either a MongoDB
        filter dict or a :class:`~django.db.models.query_utils.Q`
        instance that selects the records to update. `update_dict` is
        a MongoDB style update document containing either a new
        document or atomic modifiers such as ``$inc``.

        Keyword arguments will be passed to :meth:`pymongo.Collection.update`.
        """
        if isinstance(spec_or_q, dict):
            queryset = self.get_raw_query_set(spec_or_q)
        else:
            queryset = self.filter(spec_or_q)
        queryset._for_write = True
        compiler = _compiler_for_queryset(queryset, 'SQLUpdateCompiler')
        compiler.execute_update(update_dict, **kwargs)
    raw_update.alters_data = True


class FindAndModifyQuery(UpdateQuery, SQLQuery):
    def __init__(self, model, modify_args, db):
        super(FindAndModifyQuery, self).__init__(model)
        self.add_update_values(modify_args)
        compiler = self.get_compiler(db)
        self._modify_args = compiler._get_update_values()

    def clone(self, *args, **kwargs):
        clone = super(FindAndModifyQuery, self).clone(*args, **kwargs)
        clone._modify_args = self._modify_args
        return clone


class FindAndModifyMixin:
    def get_find_and_modify_query_set(self, modify_args):
        query = FindAndModifyQuery(self.model, modify_args,
                                   self._db or router.db_for_write(self.model))
        return QuerySet(self.model, query, self._db)

    def find_and_modify(self, **kwargs):
        """A wrapper around the findAndModify functionality of MongoDB

        Notes:
        * This will always return either one or zero records.
        * It's best to only use "get()" beside this to avoid confusion.
        * This method will probably not error if used with other methods, but
            the behavior may be confusing or erratic. Use with caution.
        * When using 'count()' with this method, the modify portion is not
            performed, and the count is counting all objects that match the
            filters.
        * 'delete()' will delete all records matching the filters.
        * Slicing and skipping is not supported by findAndModify.

        Example:
        <Model>.objects.find_and_modify(locked=True).get(id=<ID>)

        Resulting query:
        db.<Model_collection>.findAndModify(
                        {"find": {'_id': ObjectId(<ID>)},
                         'update': {'$set': {'locked': true}},
                         'new': true})})
        """
        self._for_write = True
        return self.get_find_and_modify_query_set(kwargs)
    find_and_modify.alters_data = True


class MapReduceResult(object):
    """
    Represents one item of a MapReduce result array.

    :param model: the model on that query the MapReduce was performed
    :param key: the *key* from the result item
    :param value: the *value* from the result item
    """

    def __init__(self, model, key, value):
        self.model = model
        self.key = key
        self.value = value

    @classmethod
    def from_entity(cls, model, entity):
        return cls(model, entity['_id'], entity['value'])

    def __repr__(self):
        return '<%s model=%r key=%r value=%r>' % (self.__class__.__name__,
                                                  self.model.__name__,
                                                  self.key, self.value)


class MongoDBQuerySet(QuerySet):

    def map_reduce(self, *args, **kwargs):
        """
        Performs a Map/Reduce operation on all documents matching the query,
        yielding a :class:`MapReduceResult` object for each result entity.

        If the optional keyword argument `drop_collection` is ``True``, the
        result collection will be dropped after fetching all results.

        Any other arguments are passed to :meth:`Collection.map_reduce
        <pymongo.collection.Collection.map_reduce>`.
        """
        # TODO: Field name substitution (e.g. id -> _id).
        drop_collection = kwargs.pop('drop_collection', False)
        query = self._get_query()
        kwargs.setdefault('query', query.mongo_query)
        result_collection = query.collection.map_reduce(*args, **kwargs)
        # TODO: Get rid of this.
        # PyPy has no guaranteed garbage collection so we can't rely on
        # the 'finally' suite of a generator (_map_reduce_cpython) to
        # be executed in time (in fact, it isn't guaranteed to be
        # executed *at all*). On the other hand, we *must* drop the
        # collection if `drop_collection` is True so we can't use a
        # generator in this case.
        if drop_collection and ON_PYPY:
            return self._map_reduce_pypy_drop_collection_hack(
                result_collection)
        else:
            return self._map_reduce_cpython(result_collection,
                                            drop_collection)

    def _map_reduce_cpython(self, result_collection, drop_collection):
        try:
            for entity in result_collection.find():
                yield MapReduceResult.from_entity(self.model, entity)
        finally:
            if drop_collection:
                result_collection.drop()

    def _map_reduce_pypy_drop_collection_hack(self, result_collection):
        try:
            return iter([MapReduceResult.from_entity(self.model, entity)
                         for entity in result_collection.find()])
        finally:
            result_collection.drop()

    def inline_map_reduce(self, *args, **kwargs):
        """
        Similar to :meth:`map_reduce` but runs the Map/Reduce in memory,
        returning a list of :class:`MapReduceResults <MapReduceResult>`.

        Does not take the `drop_collection` keyword argument since no result
        collection is involved for in-memory Map/Reduce operations.
        """
        query = self._get_query()
        kwargs.setdefault('query', query.mongo_query)
        return [MapReduceResult.from_entity(self.model, entity) for entity in
                query.collection.inline_map_reduce(*args, **kwargs)]

    def _get_query(self, which='SQLCompiler'):
        return _compiler_for_queryset(self, which=which).build_query()

    def distinct(self, *args, **kwargs):
        query = self._get_query()
        return query.get_cursor().distinct(*args, **kwargs)


class MongoDBManager(models.Manager, RawQueryMixin, FindAndModifyMixin):
    """
    Lets you use Map/Reduce and raw query/update with your models::

        class FooModel(models.Model):
            ...
            objects = MongoDBManager()
    """

    def map_reduce(self, *args, **kwargs):
        return self.get_query_set().map_reduce(*args, **kwargs)

    def inline_map_reduce(self, *args, **kwargs):
        return self.get_query_set().inline_map_reduce(*args, **kwargs)

    def get_query_set(self):
        return MongoDBQuerySet(self.model, using=self._db)

    def distinct(self, *args, **kwargs):
        """
        Runs a :meth:`~pymongo.Collection.distinct` query against the
        database.
        """
        return self.get_query_set().distinct(*args, **kwargs)
