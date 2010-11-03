import sys
import re

from functools import wraps

from django.db.utils import DatabaseError
from django.db.models.fields import NOT_PROVIDED

from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import MULTI, SINGLE

import pymongo
from pymongo.objectid import ObjectId

from djangotoolbox.db.basecompiler import NonrelQuery, NonrelCompiler, \
    NonrelInsertCompiler, NonrelUpdateCompiler, NonrelDeleteCompiler

from .query import A

def safe_regex(regex, *re_args, **re_kwargs):
    def wrapper(value):
        return re.compile(regex % re.escape(value), *re_args, **re_kwargs)
    wrapper.__name__ = 'safe_regex (%r)' % regex
    return wrapper

OPERATORS_MAP = {
    'exact':        lambda val: val,
    'iexact':       safe_regex('^%s$', re.IGNORECASE),
    'startswith':   safe_regex('^%s'),
    'istartswith':  safe_regex('^%s', re.IGNORECASE),
    'endswith':     safe_regex('%s$'),
    'iendswith':    safe_regex('%s$', re.IGNORECASE),
    'contains':     safe_regex('%s'),
    'icontains':    safe_regex('%s', re.IGNORECASE),
    'regex':    lambda val: re.compile(val),
    'iregex':   lambda val: re.compile(val, re.IGNORECASE),
    'gt':       lambda val: {'$gt': val},
    'gte':      lambda val: {'$gte': val},
    'lt':       lambda val: {'$lt': val},
    'lte':      lambda val: {'$lte': val},
    'range':    lambda val: {'$gte': val[0], '$lte': val[1]},
#    'year':     lambda val: {'$gte': val[0], '$lt': val[1]},
    'isnull':   lambda val: None if val else {'$ne': None},
    'in':       lambda val: {'$in': val},
}

NEGATED_OPERATORS_MAP = {
    'exact':    lambda val: {'$ne': val},
    'gt':       lambda val: {'$lte': val},
    'gte':      lambda val: {'$lt': val},
    'lt':       lambda val: {'$gte': val},
    'lte':      lambda val: {'$gt': val},
    'isnull':   lambda val: {'$ne': None} if val else None,
    'in':       lambda val: {'$nin': val},
}

def first(test_func, iterable):
    for item in iterable:
        if test_func(item):
            return item

def safe_generator(func):
    @wraps(func)
    def _func(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
            for item in ret:
                yield item
        except pymongo.errors.PyMongoError, e:
            raise DatabaseError, DatabaseError(str(e)), sys.exc_info()[2]
    return _func

def safe_call(func):
    @wraps(func)
    def _func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except pymongo.errors.PyMongoError, e:
            raise DatabaseError, DatabaseError(str(e)), sys.exc_info()[2]
    return _func

class DBQuery(NonrelQuery):
    # ----------------------------------------------
    # Public API
    # ----------------------------------------------
    def __init__(self, compiler, fields):
        super(DBQuery, self).__init__(compiler, fields)
        db_table = self.query.get_meta().db_table
        self._collection = self.connection.db_connection[db_table]
        self._ordering = []
        self.db_query = {}

    # This is needed for debugging
    def __repr__(self):
        return '<DBQuery: %r ORDER %r>' % (self.db_query, self._ordering)

    @property
    def collection(self):
        return self._collection

    @safe_generator
    def fetch(self, low_mark, high_mark):
        results = self._get_results()
        primarykey_column = self.query.get_meta().pk.column
        for entity in results:
            entity[primarykey_column] = entity.pop('_id')
            yield entity

    @safe_call
    def count(self, limit=None):
        results = self._get_results()
        if limit is not None:
            results.limit(limit)
        return results.count()

    @safe_call
    def delete(self):
        self._collection.remove(self.db_query)

    @safe_call
    def order_by(self, ordering):
        for order in ordering:
            if order.startswith('-'):
                order, direction = order[1:], pymongo.DESCENDING
            else:
                direction = pymongo.ASCENDING
            if order == self.query.get_meta().pk.column:
                order = '_id'
            self._ordering.append((order, direction))
        return self

    # This function is used by the default add_filters() implementation
    @safe_call
    def add_filter(self, column, lookup_type, negated, db_type, value):
        # Emulated/converted lookups

        if isinstance(value, A):
            field = [ f for f in self.fields if f.name == column][0]
            column, value = value.as_q(field)

        if column == self.query.get_meta().pk.column:
            column = '_id'

        if negated and lookup_type in NEGATED_OPERATORS_MAP:
            op = NEGATED_OPERATORS_MAP[lookup_type]
            negated = False
        else:
            op = OPERATORS_MAP[lookup_type]

        # TODO: does not work yet (need field)
        value = op(self.convert_value_for_db(db_type, value))

        if negated:
            value = {'$not': value}

        self._add_filter(column, lookup_type, db_type, value)

    def _add_filter(self, column, lookup_type, db_type, value):
        query = self.db_query
        # Extend existing filters if there are multiple filter() calls
        # on the same field
        if column in query:
            existing = query[column]
            if isinstance(existing, dict):
                keys = tuple(existing.keys())
                if len(keys) != 1:
                    raise NotImplementedError(
                        'Unsupported filter combination on column %s: '
                        '%r and %r' % (column, existing, value))
                key = keys[0]
                if isinstance(value, dict):
                    inequality = ('$gt', '$lt', '$gte', '$lte')
                    if key in inequality and value.keys()[0] in inequality:
                        existing.update(value)
                    else:
                        raise NotImplementedError(
                            'Unsupported filter combination on column %s: '
                            '%r and %r' % (column, existing, value))
                else:
                    if key == '$all':
                        existing['$all'].append(value)
                    else:
                        raise NotImplementedError(
                            'Unsupported filter combination on column %s: '
                            '%r and %r' % (column, existing, value))
            else:
                query[column] = {'$all': [existing, value]}
        else:
            query[column] = value

    def _get_results(self):
        results = self._collection.find(self.db_query)
        if self._ordering:
            results.sort(self._ordering)
        if self.query.low_mark > 0:
            results.skip(self.query.low_mark)
        if self.query.high_mark is not None:
            results.limit(self.query.high_mark - self.query.low_mark)
        return results

class SQLCompiler(NonrelCompiler):
    """
    A simple query: no joins, no distinct, etc.
    """
    query_class = DBQuery

    def get_filters(self, where):
        if where.connector != "AND":
            raise Exception("MongoDB only supports joining "
                "filters with and, not or.")
        assert where.connector == "AND"
        filters = {}
        for child in where.children:
            if isinstance(child, self.query.where_class):
                child_filters = self.get_filters(child)
                for k, v in child_filters.iteritems():
                    assert k not in filters
                    if where.negated:
                        filters.update(self.negate(k, v))
                    else:
                        filters[k] = v
            else:
                try:
                    field, val = self.make_atom(*child, negated=where.negated)
                    filters[field] = val
                except NotImplementedError:
                    pass
        return filters

    def make_atom(self, lhs, lookup_type, value_annotation, params_or_value, negated):

        if hasattr(lhs, "process"):
            lhs, params = lhs.process(
                lookup_type, params_or_value, self.connection
            )
        else:
            # apparently this code is never executed
            assert 0
            params = Field().get_db_prep_lookup(lookup_type, params_or_value,
                connection=self.connection, prepared=True)
        assert isinstance(lhs, (list, tuple))
        table, column, _ = lhs
        assert table == self.query.model._meta.db_table
        if column == self.query.model._meta.pk.column:
            column = "_id"

        val = self.convert_value_for_db(_, params[0])
        return column, val

    def _split_db_type(self, db_type):
        try:
            db_type, db_subtype = db_type.split(':', 1)
        except ValueError:
            db_subtype = None
        return db_type, db_subtype

    def convert_value_for_db(self, db_type, value):
        if db_type is None or value is None:
            return value

        db_type, db_subtype = self._split_db_type(db_type)
        if db_subtype is not None:
            if isinstance(value, (set, list, tuple)):
                # Sets are converted to lists here because MongoDB has not sets.
                return [self.convert_value_for_db(db_subtype, subvalue)
                        for subvalue in value]
            elif isinstance(value, dict):
                return dict((key, self.convert_value_for_db(db_subtype, subvalue))
                            for key, subvalue in value.iteritems())

        else:
            if isinstance(value, list):
                # most likely a list of ObjectIds when doing a .delete() query
                value = [self.convert_value_for_db(db_type, val) for val in value]
            elif db_type == 'objectid':
                # single ObjectId
                return ObjectId(value)

        # Pass values of any type not covered above as they are.
        # PyMongo will complain if they can't be encoded.
        return value

    def convert_value_from_db(self, db_type, value):
        if db_type is None:
            return value

        if value is None or value is NOT_PROVIDED:
            # ^^^ it is *crucial* that this is not written as 'in (None, NOT_PROVIDED)'
            # because that would call value's __eq__ method, which in case value
            # is an instance of serializer.LazyModelInstance does a database query.
            return None

        db_type, db_subtype = self._split_db_type(db_type)
        if db_subtype is not None:
            for field, type_ in [('SetField', set), ('ListField', list)]:
                if db_type == field:
                    return type_(self.convert_value_from_db(db_subtype, subvalue)
                                 for subvalue in value)
            if db_type == 'DictField':
                return dict((key, self.convert_value_from_db(db_subtype, subvalue))
                            for key, subvalue in value.iteritems())

        if db_type == 'objectid':
            return unicode(value)

        return value

    def insert_params(self):
        conn = self.connection
        params = {'safe': conn.safe_inserts}
        if conn.wait_for_slaves:
            params['w'] = conn.wait_for_slaves
        return params

    @property
    def _collection(self):
        connection = self.connection.db_connection
        db_table = self.query.get_meta().db_table
        return connection[db_table]

    def _save(self, data, return_id=False):
        primary_key = self._collection.save(data, **self.insert_params())
        if return_id:
            return unicode(primary_key)

    def execute_sql(self, result_type=MULTI):
        """
        Handles aggregate/count queries
        """
        aggregations = self.query.aggregate_select.items()

        if len(aggregations) == 1 and isinstance(aggregations[0][1], sqlaggregates.Count):
            # Ne need for full-featured aggregation processing if we only
            # want to count() -- let djangotoolbox's simple Count aggregation
            # implementation handle this case.
            return super(SQLCompiler, self).execute_sql(result_type)

        from .contrib import aggregations as aggregations_module
        sqlagg, reduce, finalize, order, initial = [], [], [], [], {}
        query = self.build_query()

        # First aggregations implementation
        # THIS CAN/WILL BE IMPROVED!!!
        for alias, aggregate in aggregations:
            if isinstance(aggregate, sqlaggregates.Aggregate):
                if isinstance(aggregate, sqlaggregates.Count):
                    order.append(None)
                    # Needed to keep the iteration order which is important in the returned value.
                    sqlagg.append(self.get_count())
                    continue

                aggregate_class = getattr(aggregations_module, aggregate.__class__.__name__)

                field = aggregate.source.name if aggregate.source else '_id'
                if alias is None:
                    alias = '_id__%s' % cls_name
                aggregate = aggregate_class(field, **aggregate.extra)
                aggregate.add_to_query(self.query, alias, aggregate.col, aggregate.source,
                                       aggregate.extra.get("is_summary", False))

            order.append(aggregate.alias) # just to keep the right order
            initial_, reduce_, finalize_ = aggregate.as_query(query)
            initial.update(initial_)
            reduce.append(reduce_)
            finalize.append(finalize_)

        cursor = query.collection.group(None,
                            query.db_query,
                            initial,
                            reduce="function(doc, out){ %s }" % "; ".join(reduce),
                            finalize="function(out){ %s }" % "; ".join(finalize))

        ret = []
        for alias in order:
            result = cursor[0][alias] if alias else sqlagg.pop(0)
            if result_type is MULTI:
                result = [result]
            ret.append(result)
        return ret

class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):
    @safe_call
    def insert(self, data, return_id=False):
        pk_column = self.query.get_meta().pk.column
        try:
            data['_id'] = data.pop(pk_column)
        except KeyError:
            pass
        return self._save(data, return_id)

# TODO: Define a common nonrel API for updates and add it to the nonrel
# backend base classes and port this code to that API
class SQLUpdateCompiler(NonrelUpdateCompiler, SQLCompiler):
    query_class = DBQuery

    @safe_call
    def execute_sql(self, return_id=False):
        filters = self.get_filters(self.query.where)

        vals = {}
        for field, o, value in self.query.values:
            if hasattr(value, 'prepare_database_save'):
                value = value.prepare_database_save(field)
            else:
                value = field.get_db_prep_save(value, connection=self.connection)

            value = self.convert_value_for_db(field.db_type(), value)

            if hasattr(value, "evaluate"):
                assert value.connector in (value.ADD, value.SUB)
                assert not value.negated
                assert not value.subtree_parents
                lhs, rhs = value.children
                if isinstance(lhs, F):
                    assert not isinstance(rhs, F)
                    if value.connector == value.SUB:
                        rhs = -rhs
                else:
                    assert value.connector == value.ADD
                    rhs, lhs = lhs, rhs
                vals.setdefault("$inc", {})[lhs.name] = rhs
            else:
                vals.setdefault("$set", {})[field.column] = value
        return self._collection.update(
            filters,
            vals,
            multi=True
        )

class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass
