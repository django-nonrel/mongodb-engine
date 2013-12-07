import sys
import re

from django.db import models, connections
from django.db.models.query import QuerySet
from django.db.models.sql.query import Query as SQLQuery
from django.db.models.query_utils import Q
from django.db.models.constants import LOOKUP_SEP
from django_mongodb_engine.compiler import OPERATORS_MAP, NEGATED_OPERATORS_MAP
from djangotoolbox.fields import AbstractIterableField


ON_PYPY = hasattr(sys, 'pypy_version_info')
ALL_OPERATORS = dict(list(OPERATORS_MAP.items() + NEGATED_OPERATORS_MAP.items())).keys()
MONGO_DOT_FIELDS = ('DictField', 'ListField', 'SetField', 'EmbeddedModelField')


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

    def _filter_or_exclude(self, negate, *args, **kwargs):
        if args or kwargs:
            assert self.query.can_filter(), \
                    "Cannot filter a query once a slice has been taken."

        clone = self._clone()

        self._process_arg_filters(args, kwargs)

        if negate:
            clone.query.add_q(~Q(*args, **kwargs))
        else:
            clone.query.add_q(Q(*args, **kwargs))
        return clone

    def _get_mongo_field_names(self):
        if not hasattr(self, '_mongo_field_names'):
            self._mongo_field_names = []
            for name in self.model._meta.get_all_field_names():
                field = self.model._meta.get_field_by_name(name)[0]
                if '.' not in name and field.get_internal_type() in MONGO_DOT_FIELDS:
                    self._mongo_field_names.append(name)

        return self._mongo_field_names

    def _process_arg_filters(self, args, kwargs):
        for key, val in kwargs.items():
            del kwargs[key]
            key = self._dotify_field_name(key)
            kwargs[key] = val
            self._maybe_add_dot_field(key)

        for a in args:
            if isinstance(a, Q):
               self._process_q_filters(a)

    def _process_q_filters(self, q):
        for c in range(len(q.children)):
            child = q.children[c]
            if isinstance(child, Q):
                self._process_q_filters(child)
            elif isinstance(child, tuple):
                key, val = child
                key = self._dotify_field_name(key)
                q.children[c] = (key, val)
                self._maybe_add_dot_field(key)

    def _dotify_field_name(self, name):
        if LOOKUP_SEP in name and name.split(LOOKUP_SEP)[0] in self._get_mongo_field_names():
            for op in ALL_OPERATORS:
                if name.endswith(op):
                    name = re.sub(LOOKUP_SEP + op + '$', '#' + op, name)
                    break
            name = name.replace(LOOKUP_SEP, '.').replace('#', LOOKUP_SEP)

        return name

    def _maybe_add_dot_field(self, name):
        name = name.split(LOOKUP_SEP)[0]

        if '.' in name and name not in self.model._meta.get_all_field_names():
            parts1 = name.split('.')
            parts2 = []
            parts3 = []
            model = self.model

            while len(parts1) > 0:
                part = parts1.pop(0)
                field = model._meta.get_field_by_name(part)[0]
                field_type = field.get_internal_type()
                if field_type not in MONGO_DOT_FIELDS:
                    # FIXME: In this case, we are handling embedded fields
                    # and should probably use the actual field class
                    # instead of AbstractIterableField for the lookup.
                    pass
                column = field.db_column
                if column:
                    part = column
                parts2.append(part)
                if field_type == 'ListField':
                    list_type = field.item_field.get_internal_type()
                    if list_type == 'EmbeddedModelField':
                        field = field.item_field
                        field_type = list_type
                if field_type == 'EmbeddedModelField':
                    model = field.embedded_model()
                else:
                    while len(parts1) > 0:
                        part = parts1.pop(0)
                        if field_type in MONGO_DOT_FIELDS:
                            parts2.append(part)
                        else:
                            parts3.append(part)
            db_column = LOOKUP_SEP.join(['.'.join(parts2)] + parts3)

            field = AbstractIterableField(
                db_column = db_column,
                blank=True,
                null=True,
                editable=False,
            )
            field.contribute_to_class(self.model, name)

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

    def _get_query(self):
        return _compiler_for_queryset(self).build_query()

    def distinct(self, *args, **kwargs):
        query = self._get_query()
        return query.get_cursor().distinct(*args, **kwargs)


class MongoDBManager(models.Manager, RawQueryMixin):
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
