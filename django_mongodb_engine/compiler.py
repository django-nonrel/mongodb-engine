import re
import sys
import datetime

from functools import wraps

from django.db.utils import DatabaseError
from django.db.models.fields import NOT_PROVIDED
from django.db.models import F
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import MULTI, SINGLE
from django.db.models.sql.where import AND, OR
from django.utils.tree import Node

from pymongo.errors import PyMongoError
from pymongo import ASCENDING, DESCENDING
from pymongo.objectid import ObjectId, InvalidId

from djangotoolbox.db.basecompiler import NonrelQuery, NonrelCompiler, \
    NonrelInsertCompiler, NonrelUpdateCompiler, NonrelDeleteCompiler

from .query import A
from .aggregations import get_aggregation_class_by_name
from .contrib import RawQuery
from .utils import safe_regex, first

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
    'in':       lambda val: {'$nin' : val}
}

def safe_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PyMongoError, e:
            raise DatabaseError, DatabaseError(str(e)), sys.exc_info()[2]
    return wrapper

class MongoQuery(NonrelQuery):
    def __init__(self, compiler, fields):
        super(MongoQuery, self).__init__(compiler, fields)
        db_table = self.query.get_meta().db_table
        self.collection = self.connection.get_collection(db_table)
        self._ordering = []
        self._mongo_query = getattr(compiler.query, 'raw_query', {})

    def __repr__(self):
        return '<MongoQuery: %r ORDER %r>' % (self._mongo_query, self._ordering)

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
    def order_by(self, ordering):
        for order in ordering:
            if order.startswith('-'):
                order, direction = order[1:], DESCENDING
            else:
                direction = ASCENDING
            if order == self.query.get_meta().pk.column:
                order = '_id'
            self._ordering.append((order, direction))
        return self

    @safe_call
    def delete(self):
        options = self.connection.operation_flags.get('delete', {})
        self.collection.remove(self._mongo_query, **options)

    def _get_results(self):
        fields = None
        if self.query.select_fields and not self.query.aggregates:
            fields = dict((field.column, 1) for field in self.query.select_fields)
        results = self.collection.find(self._mongo_query, fields=fields)
        if self._ordering:
            results.sort(self._ordering)
        if self.query.low_mark > 0:
            results.skip(self.query.low_mark)
        if self.query.high_mark is not None:
            results.limit(self.query.high_mark - self.query.low_mark)
        return results

    def add_filters(self, filters, query=None):
        children = self._get_children(filters.children)

        if query is None:
            query = self._mongo_query

        if filters.connector is OR:
            or_conditions = query['$or'] = []

        if filters.negated:
            self._negated = not self._negated

        for child in children:
            if filters.connector is OR:
                subquery = {}
            else:
                subquery = query

            if isinstance(child, Node):
                if filters.connector is OR and child.connector is OR:
                    if len(child.children) > 1:
                        raise DatabaseError("Nested ORs are not supported")

                if filters.connector is OR and filters.negated:
                    raise NotImplementedError("Negated ORs are not implemented")

                self.add_filters(child, query=subquery)

                if filters.connector is OR and subquery:
                    or_conditions.extend(subquery.pop('$or', []))
                    or_conditions.append(subquery)
            else:
                column, lookup_type, db_type, value = self._decode_child(child)
                if lookup_type in ('year', 'month', 'day'):
                    raise DatabaseError("MongoDB does not support year/month/day queries")
                if column == self.query.get_meta().pk.column:
                    column = '_id'

                existing = subquery.get(column)

                if self._negated and isinstance(existing, dict) and '$ne' in existing:
                    raise DatabaseError(
                        "Negated conditions can not be used in conjunction ( ~Q1 & ~Q2 )\n"
                        "Try replacing your condition with  ~Q(foo__in=[...])"
                    )

                if isinstance(value, A):
                    field = first(lambda field: field.column == column, self.fields)
                    column, value = value.as_q(field)

                if self._negated:
                    if lookup_type in NEGATED_OPERATORS_MAP:
                        op_func = NEGATED_OPERATORS_MAP[lookup_type]
                    else:
                        def op_func(value):
                            return {'$not' : OPERATORS_MAP[lookup_type](value)}
                else:
                    op_func = OPERATORS_MAP[lookup_type]

                if lookup_type == 'isnull':
                    value = op_func(value)
                else:
                    value = op_func(self.convert_value_for_db(db_type, value))

                if existing is not None:
                    key = '$all' if not self._negated else '$nin'
                    if isinstance(value, dict):
                        assert isinstance(existing, dict)
                        existing.update(value)
                    else:
                        if isinstance(existing, dict) and key in existing:
                            existing[key].append(value)
                        else:
                            if isinstance(existing, dict):
                                existing.update({key: value})
                            else:
                                subquery[column] = {key: [existing, value]}
                else:
                    subquery[column] = value

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

    def _split_db_type(self, db_type):
        try:
            db_type, db_subtype = db_type.split(':', 1)
        except ValueError:
            db_subtype = None
        return db_type, db_subtype

    @safe_call # see #7
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

        if isinstance(value, (set, list, tuple)):
            # most likely a list of ObjectIds when doing a .delete() query
            return [self.convert_value_for_db(db_type, val) for val in value]

        if db_type == 'objectid':
            try:
                return ObjectId(value)
            except InvalidId:
                # Provide a better message for invalid IDs
                assert isinstance(value, unicode)
                if len(value) > 13:
                    value = value[:10] + '...'
                msg = "AutoField (default primary key) values must be strings " \
                      "representing an ObjectId on MongoDB (got %r instead)" % value
                if self.query.model._meta.db_table == 'django_site':
                    # Also provide some useful tips for (very common) issues
                    # with settings.SITE_ID.
                    msg += ". Please make sure your SITE_ID contains a valid ObjectId string."
                raise InvalidId(msg)

        # Pass values of any type not covered above as they are.
        # PyMongo will complain if they can't be encoded.
        return value

    @safe_call # see #7
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

        if db_type == 'date':
            return datetime.date(value.year, value.month, value.day)

        if db_type == 'time':
            return datetime.time(value.hour, value.minute, value.second,
                                 value.microsecond)
        return value

    def _save(self, data, return_id=False):
        collection = self.get_collection()
        options = self.connection.operation_flags.get('save', {})
        if data.get('_id', NOT_PROVIDED) is None:
            if len(data) == 1:
                # insert with empty model
                data = {}
            else:
                raise DatabaseError("Can't save entity with _id set to None")
        primary_key = collection.save(data, **options)
        if return_id:
            return unicode(primary_key)

    def execute_sql(self, result_type=MULTI):
        """
        Handles aggregate/count queries
        """
        aggregations = self.query.aggregate_select.items()

        if len(aggregations) == 1 and isinstance(aggregations[0][1], sqlaggregates.Count):
            # Ne need for full-featured aggregation processing if we only want to count()
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
                # Needed to keep the iteration order which is important in the returned value.
                # XXX this actually does a separate query... performance?
                counts.append(self.get_count())
                continue

            aggregate_class = get_aggregation_class_by_name(aggregate.__class__.__name__)
            lookup = aggregate.col
            if isinstance(lookup, tuple):
                # lookup is a (table_name, column_name) tuple.
                # Get rid of the table name as aggregations can't span
                # multiple tables anyway
                if lookup[0] != query.collection.name:
                    raise DatabaseError("Aggregations can not span multiple tables (tried %r and %r)"
                                        % (lookup[0], query.collection.name))
                lookup = lookup[1]
            self.query.aggregates[alias] = aggregate = aggregate_class(alias, lookup, aggregate.source)
            order.append(alias) # just to keep the right order
            initial.update(aggregate.initial())
            reduce.append(aggregate.reduce())
            finalize.append(aggregate.finalize())

        reduce = "function(doc, out){ %s }" % "; ".join(reduce)
        finalize = "function(out){ %s }" % "; ".join(finalize)
        cursor = query.collection.group(None, query._mongo_query, initial, reduce, finalize)

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
        pk_column = self.query.get_meta().pk.column
        try:
            data['_id'] = data.pop(pk_column)
        except KeyError:
            pass
        return self._save(data, return_id)

# TODO: Define a common nonrel API for updates and add it to the nonrel
# backend base classes and port this code to that API
class SQLUpdateCompiler(NonrelUpdateCompiler, SQLCompiler):
    query_class = MongoQuery

    @safe_call
    def execute_raw(self, update_spec, multi=True, **kwargs):
        collection = self.get_collection()
        criteria = self.build_query()._mongo_query
        options = self.connection.operation_flags.get('update', {})
        options = dict(options, **kwargs)
        return collection.update(criteria, update_spec, multi=multi, **options)

    def execute_sql(self, return_id=False):
        return self.execute_raw(*self._get_update_spec())

    def _get_update_spec(self):
        multi = True
        spec = {}
        for field, _, value in self.query.values:
            if getattr(field, 'forbids_updates', False):
                raise DatabaseError("Updates on %ss are not allowed" %
                                    field.__class__.__name__)
            if field.unique:
                multi = False
            if hasattr(value, 'prepare_database_save'):
                value = value.prepare_database_save(field)
            else:
                value = field.get_db_prep_save(value, connection=self.connection)

            value = self.convert_value_for_db(field.db_type(connection=self.connection), value)
            if hasattr(value, "evaluate"):
                assert value.connector in (value.ADD, value.SUB)
                assert not value.negated
                assert not value.subtree_parents
                lhs, rhs = value.children
                if isinstance(lhs, F):
                    assert not isinstance(rhs, F)
                    assert lhs.name == field.name
                    if value.connector == value.SUB:
                        rhs = -rhs
                else:
                    assert value.connector == value.ADD
                    rhs, lhs = lhs, rhs
                action, column, value = '$inc', lhs.name, rhs
            else:
                action, column, value = '$set', field.column, value
            if column == self.query.get_meta().pk.column:
                raise DatabaseError("Can not modify _id")
            spec.setdefault(action, {})[column] = value

        return spec, multi

class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass
