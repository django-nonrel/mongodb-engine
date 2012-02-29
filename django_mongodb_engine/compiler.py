import datetime
from functools import wraps
import re
import sys

from django.db.models import F
from django.db.models.fields import AutoField
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import MULTI
from django.db.models.sql.where import OR
from django.db.utils import DatabaseError, IntegrityError
from django.utils.tree import Node

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError

from djangotoolbox.db.basecompiler import (
    NonrelQuery,
    NonrelCompiler,
    NonrelInsertCompiler,
    NonrelUpdateCompiler,
    NonrelDeleteCompiler)

from .aggregations import get_aggregation_class_by_name
from .query import A
from .utils import safe_regex, first


# Mongo wants string-based AutoFields.
AutoField.value_type = unicode


OPERATORS_MAP = {
    'exact':  lambda val: val,
    'gt':     lambda val: {'$gt': val},
    'gte':    lambda val: {'$gte': val},
    'lt':     lambda val: {'$lt': val},
    'lte':    lambda val: {'$lte': val},
    'in':     lambda val: {'$in': val},
    'range':  lambda val: {'$gte': val[0], '$lte': val[1]},
    'isnull': lambda val: None if val else {'$ne': None},

    # Regex matchers.
    'iexact':      safe_regex('^%s$', re.IGNORECASE),
    'startswith':  safe_regex('^%s'),
    'istartswith': safe_regex('^%s', re.IGNORECASE),
    'endswith':    safe_regex('%s$'),
    'iendswith':   safe_regex('%s$', re.IGNORECASE),
    'contains':    safe_regex('%s'),
    'icontains':   safe_regex('%s', re.IGNORECASE),
    'regex':       lambda val: re.compile(val),
    'iregex':      lambda val: re.compile(val, re.IGNORECASE),

    # Date OPs.
    'year': lambda val: {'$gte': val[0], '$lt': val[1]},
}

NEGATED_OPERATORS_MAP = {
    'exact':  lambda val: {'$ne': val},
    'gt':     lambda val: {'$lte': val},
    'gte':    lambda val: {'$lt': val},
    'lt':     lambda val: {'$gte': val},
    'lte':    lambda val: {'$gt': val},
    'in':     lambda val: {'$nin': val},
    'isnull': lambda val: {'$ne': None} if val else None,
}


def safe_call(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DuplicateKeyError, e:
            raise IntegrityError, IntegrityError(str(e)), sys.exc_info()[2]
        except PyMongoError, e:
            raise DatabaseError, DatabaseError(str(e)), sys.exc_info()[2]

    return wrapper


def get_pk_column(duck):
    return duck.query.get_meta().pk.column


class MongoQuery(NonrelQuery):

    def __init__(self, compiler, fields):
        super(MongoQuery, self).__init__(compiler, fields)
        db_table = self.query.get_meta().db_table
        self.collection = self.connection.get_collection(db_table)
        self._ordering = []
        self._mongo_query = getattr(compiler.query, 'raw_query', {})

    def __repr__(self):
        return '<MongoQuery: %r ORDER %r>' % \
               (self._mongo_query, self._ordering)

    def fetch(self, low_mark, high_mark):
        results = self._get_results()
        for entity in results:
            entity[get_pk_column(self)] = entity.pop('_id')
            yield entity

    @safe_call
    def count(self, limit=None):
        results = self._get_results()
        if limit is not None:
            results.limit(limit)
        return results.count()

    @safe_call
    def order_by(self, ordering):
        for column, descending in ordering:
            direction = DESCENDING if descending else ASCENDING
            if column == get_pk_column(self):
                column = '_id'
            self._ordering.append((column, direction))
        return self

    @safe_call
    def delete(self):
        options = self.connection.operation_flags.get('delete', {})
        self.collection.remove(self._mongo_query, **options)

    def _get_results(self):
        if self.query.low_mark == self.query.high_mark:
            return []
        fields = None
        if self.query.select_fields and not self.query.aggregates:
            fields = dict((field.column, 1)
                          for field in self.query.select_fields)
        results = self.collection.find(self._mongo_query, fields=fields)
        if self._ordering:
            results.sort(self._ordering)
        if self.query.low_mark > 0:
            results.skip(self.query.low_mark)
        if self.query.high_mark is not None:
            results.limit(int(self.query.high_mark - self.query.low_mark))
        return results

    def add_filters(self, filters, query=None):
        children = self._get_children(filters.children)

        if query is None:
            query = self._mongo_query

        if filters.connector == OR:
            assert '$or' not in query, "Multiple ORs are not supported."
            or_conditions = query['$or'] = []

        if filters.negated:
            self._negated = not self._negated

        for child in children:
            if filters.connector == OR:
                subquery = {}
            else:
                subquery = query

            if isinstance(child, Node):
                if filters.connector == OR and child.connector == OR:
                    if len(child.children) > 1:
                        raise DatabaseError("Nested ORs are not supported.")

                if filters.connector == OR and filters.negated:
                    raise NotImplementedError("Negated ORs are not supported.")

                self.add_filters(child, query=subquery)

                if filters.connector == OR and subquery:
                    or_conditions.extend(subquery.pop('$or', []))
                    or_conditions.append(subquery)

                continue

            field, lookup_type, value = self._decode_child(child)
            column = field.column

            if lookup_type in ('month', 'day'):
                raise DatabaseError("MongoDB does not support month/day "
                                    "queries.")
            if self._negated and lookup_type == 'range':
                raise DatabaseError("Negated range lookups are not "
                                    "supported.")

            if field.primary_key:
                column = '_id'

            existing = subquery.get(column)

            if isinstance(value, A):
                column, value = value.as_q(field)

            if self._negated and lookup_type in NEGATED_OPERATORS_MAP:
                op_func = NEGATED_OPERATORS_MAP[lookup_type]
                already_negated = True
            else:
                op_func = OPERATORS_MAP[lookup_type]
                if self._negated:
                    already_negated = False

            lookup = op_func(value)

            if existing is None:
                if self._negated and not already_negated:
                    lookup = {'$not': lookup}
                subquery[column] = lookup
                query.update(subquery)
                continue

            if not isinstance(existing, dict):
                if not self._negated:
                    # {'a': o1} + {'a': o2} --> {'a': {'$all': [o1, o2]}}
                    assert not isinstance(lookup, dict)
                    subquery[column] = {'$all': [existing, lookup]}
                else:
                    # {'a': o1} + {'a': {'$not': o2}} -->
                    #     {'a': {'$all': [o1], '$nin': [o2]}}
                    if already_negated:
                        assert lookup.keys() == ['$ne']
                        lookup = lookup['$ne']
                    assert not isinstance(lookup, dict)
                    subquery[column] = {'$all': [existing], '$nin': [lookup]}
            else:
                not_ = existing.pop('$not', None)
                if not_:
                    assert not existing
                    if isinstance(lookup, dict):
                        assert lookup.keys() == ['$ne']
                        lookup = lookup.values()[0]
                    assert not isinstance(lookup, dict), (not_, lookup)
                    if self._negated:
                        # {'not': {'a': o1}} + {'a': o2} -->
                        #     {'a': {'nin': [o1], 'all': [o2]}}
                        subquery[column] = {'$nin': [not_, lookup]}
                    else:
                        # {'not': {'a': o1}} + {'a': {'not': o2}} -->
                        #     {'a': {'nin': [o1, o2]}}
                        subquery[column] = {'$nin': [not_], '$all': [lookup]}
                else:
                    if isinstance(lookup, dict):
                        if '$ne' in lookup:
                            if '$nin' in existing:
                                # {'$nin': [o1, o2]} + {'$ne': o3} -->
                                #     {'$nin': [o1, o2, o3]}
                                assert '$ne' not in existing
                                existing['$nin'].append(lookup['$ne'])
                            elif '$ne' in existing:
                                # {'$ne': o1} + {'$ne': o2} -->
                                #    {'$nin': [o1, o2]}
                                existing['$nin'] = [existing.pop('$ne'),
                                                    lookup['$ne']]
                            else:
                                existing.update(lookup)
                        else:
                            # {'$gt': o1} + {'$lt': o2} -->
                            #     {'$gt': o1, '$lt': o2}
                            assert all(key not in existing
                                       for key in lookup.keys()), \
                                       [lookup, existing]
                            existing.update(lookup)
                    else:
                        key = '$nin' if self._negated else '$all'
                        existing.setdefault(key, []).append(lookup)

                query.update(subquery)

        if filters.negated:
            self._negated = not self._negated


class SQLCompiler(NonrelCompiler):
    """
    A simple query: no joins, no distinct, etc.
    """
    query_class = MongoQuery

    def get_collection(self):
        return self.connection.get_collection(self.query.get_meta().db_table)

    def execute_sql(self, result_type=MULTI):
        """
        Handles aggregate/count queries.
        """
        aggregations = self.query.aggregate_select.items()

        if len(aggregations) == 1 and isinstance(aggregations[0][1],
                                                 sqlaggregates.Count):
            # Ne need for full-featured aggregation processing if we
            # only want to count().
            if result_type is MULTI:
                return [[self.get_count()]]
            else:
                return [self.get_count()]

        counts, reduce, finalize, order, initial = [], [], [], [], {}
        query = self.build_query()

        for alias, aggregate in aggregations:
            assert isinstance(aggregate, sqlaggregates.Aggregate)
            if isinstance(aggregate, sqlaggregates.Count):
                order.append(None)
                # Needed to keep the iteration order which is important
                # in the returned value.
                # XXX: This actually does a separate query... performance?
                counts.append(self.get_count())
                continue

            aggregate_class = get_aggregation_class_by_name(
                aggregate.__class__.__name__)
            lookup = aggregate.col
            if isinstance(lookup, tuple):
                # lookup is a (table_name, column_name) tuple.
                # Get rid of the table name as aggregations can't span
                # multiple tables anyway.
                if lookup[0] != query.collection.name:
                    raise DatabaseError("Aggregations can not span multiple "
                                        "tables (tried %r and %r)." %
                                        (lookup[0], query.collection.name))
                lookup = lookup[1]
            self.query.aggregates[alias] = aggregate = aggregate_class(
                alias, lookup, aggregate.source)
            order.append(alias) # Just to keep the right order.
            initial.update(aggregate.initial())
            reduce.append(aggregate.reduce())
            finalize.append(aggregate.finalize())

        reduce = 'function(doc, out){ %s }' % '; '.join(reduce)
        finalize = 'function(out){ %s }' % '; '.join(finalize)
        cursor = query.collection.group(None, query._mongo_query, initial,
                                        reduce, finalize)

        ret = []
        for alias in order:
            result = cursor[0][alias] if alias else counts.pop(0)
            if result_type is MULTI:
                result = [result]
            ret.append(result)
        return ret


class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):

    @safe_call
    def insert(self, data, return_id=False):
        """
        Stores a document using field columns as element names, except
        for the primary key field for which "_id" is used.

        If just a {pk_field: None} mapping is given a new empty
        document is created, otherwise value for a primary key may not
        be None.
        """
        collection = self.get_collection()
        options = self.connection.operation_flags.get('save', {})
        document = {}
        for field, value in data.iteritems():
            if field.primary_key:
                if value is None:
                    if len(data) != 1:
                        raise DatabaseError("Can't save entity with _id "
                                            "set to None.")
                else:
                    document['_id'] = value
            else:
                document[field.column] = value

        key = collection.save(document, **options)
        if return_id:
            return key


# TODO: Define a common nonrel API for updates and add it to the nonrel
#       backend base classes and port this code to that API.
class SQLUpdateCompiler(NonrelUpdateCompiler, SQLCompiler):
    query_class = MongoQuery

    def update(self, values):
        multi = True
        spec = {}
        for field, value in values:
            if field.primary_key:
                raise DatabaseError("Can not modify _id.")
            if getattr(field, 'forbids_updates', False):
                raise DatabaseError("Updates on %ss are not allowed." %
                                    field.__class__.__name__)
            if hasattr(value, 'evaluate'):
                # .update(foo=F('foo') + 42) --> {'$inc': {'foo': 42}}
                lhs, rhs = value.children
                assert (value.connector in (value.ADD, value.SUB) and
                        not value.negated and not value.subtree_parents and
                        isinstance(lhs, F) and not isinstance(rhs, F) and
                        lhs.name == field.name)
                if value.connector == value.SUB:
                    rhs = -rhs
                action = '$inc'
                value = rhs
            else:
                # .update(foo=123) --> {'$set': {'foo': 123}}
                action = '$set'
            spec.setdefault(action, {})[field.column] = value

            if field.unique:
                multi = False

        return self.execute_update(spec, multi)

    @safe_call
    def execute_update(self, update_spec, multi=True, **kwargs):
        collection = self.get_collection()
        criteria = self.build_query()._mongo_query
        options = self.connection.operation_flags.get('update', {})
        options = dict(options, **kwargs)
        info = collection.update(criteria, update_spec, multi=multi, **options)
        if info is not None:
            return info.get('n')


class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass
