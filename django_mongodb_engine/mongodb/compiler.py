import sys
import re

from datetime import datetime
from functools import wraps

import pymongo
from gridfs import GridFS
from pymongo.objectid import ObjectId

from django.conf import settings
from django.db import models
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import LOOKUP_SEP, MULTI, SINGLE
from django.db.models.sql.where import AND, OR
from django.db.utils import DatabaseError, IntegrityError
from django.db.models.sql.where import WhereNode
from django.db.models.fields import NOT_PROVIDED
from django.utils.tree import Node

from djangotoolbox.db.basecompiler import NonrelQuery, NonrelCompiler, \
    NonrelInsertCompiler, NonrelUpdateCompiler, NonrelDeleteCompiler

TYPE_MAPPING_FROM_DB = {
    'unicode':  lambda val: unicode(val),
    'int':      lambda val: int(val),
    'float':    lambda val: float(val),
    'bool':     lambda val: bool(val),
    'objectid': lambda val: unicode(val),
}

TYPE_MAPPING_TO_DB = {
    'unicode':  lambda val: unicode(val),
    'int':      lambda val: int(val),
    'float':    lambda val: float(val),
    'bool':     lambda val: bool(val),
    'date':     lambda val: datetime(val.year, val.month, val.day),
    'time':     lambda val: datetime(2000, 1, 1, val.hour, val.minute,
                                     val.second, val.microsecond),
    'objectid': lambda val: ObjectId(val),
}

OPERATORS_MAP = {
    'exact':    lambda val: val,
    'iexact':    lambda val: re.compile(r'^%s$' % val, re.IGNORECASE),
    'startswith':    lambda val: re.compile(r'%s' % val),
    'istartswith':    lambda val: re.compile(r'^%s' % val, re.IGNORECASE),
    'endswith':    lambda val: re.compile(r'%s$' % val),
    'iendswith':    lambda val: re.compile(r'%s$' % val, re.IGNORECASE),
    'contains':    lambda val: re.compile(r'%s' % val),
    'icontains':    lambda val: re.compile(r'%s' % val, re.IGNORECASE),
    'regex':    lambda val: re.compile(val),
    'iregex':   lambda val: re.compile(val, re.IGNORECASE),
    'gt':       lambda val: {'$gt': val},
    'gte':      lambda val: {'$gte': val},
    'lt':       lambda val: {'$lt': val},
    'lte':      lambda val: {'$lte': val},
    'range':    lambda val: {'$gte': val[0], '$lte': val[1]},
    'year':     lambda val: {'$gte': val[0], '$lt': val[1]},
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

def _get_mapping(db_type, value, mapping):
    # TODO - comments. lotsa comments

    if value == NOT_PROVIDED:
        return None

    if value is None:
        return None

    if db_type in mapping:
        _func = mapping[db_type]
    else:
        _func = lambda val: val
    # TODO - what if the data is represented as list on the python side?
    if isinstance(value, list):
        return map(_func, value)
    return _func(value)

def python2db(db_type, value):
    return _get_mapping(db_type, value, TYPE_MAPPING_TO_DB)

def db2python(db_type, value):
    return _get_mapping(db_type, value, TYPE_MAPPING_FROM_DB)

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

    @safe_call
    def fetch(self, low_mark, high_mark):
        results = self._get_results()
        if low_mark > 0:
            results = results.skip(low_mark)
        if high_mark is not None:
            results = results.limit(high_mark - low_mark)

        for entity in results:
            entity[self.query.get_meta().pk.column] = entity['_id']
            del entity['_id']
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

    # This function is used by the default add_filters() implementation
    @safe_call
    def add_filter(self, column, lookup_type, negated, db_type, value):
        # Emulated/converted lookups
        if column == self.query.get_meta().pk.column:
            column = '_id'

        if negated and lookup_type in NEGATED_OPERATORS_MAP:
            op = NEGATED_OPERATORS_MAP[lookup_type]
            negated = False
        else:
            op = OPERATORS_MAP[lookup_type]
        value = op(self.convert_value_for_db(db_type, value))

        if negated:
            value = {'$not': value}

        self._add_filter(column, lookup_type, db_type, value)

    # ----------------------------------------------
    # Internal API
    # ----------------------------------------------
    def _add_filter(self, column, lookup_type, db_type, value):
        query = self.db_query
        # Extend existing filters if there are multiple filter() calls
        # on the same field
        if column in query:
            existing = query[column]
            if isinstance(existing, dict):
                keys = tuple(existing.keys())
                if len(keys) != 1:
                    raise DatabaseError(
                        'Unsupported filter combination on column %s: '
                        '%r and %r' % (column, existing, value))
                key = keys[0]
                if isinstance(value, dict):
                    inequality = ('$gt', '$lt', '$gte', '$lte')
                    if key in inequality and value.keys()[0] in inequality:
                        existing.update(value)
                    else:
                        raise DatabaseError(
                            'Unsupported filter combination on column %s: '
                            '%r and %r' % (column, existing, value))
                else:
                    if key == '$all':
                        existing['$all'].append(value)
                    else:
                        raise DatabaseError(
                            'Unsupported filter combination on column %s: '
                            '%r and %r' % (column, existing, value))
            else:
                query[column] = {'$all': [existing, value]}
        else:
            query[column] = value

    def _get_results(self):
        """
        @returns: pymongo iterator over results
        defined by self.query
        """
        results = self._collection.find(self.db_query)
        if self._ordering:
            results = results.sort(self._ordering)
        return results

class SQLCompiler(NonrelCompiler):
    """
    A simple query: no joins, no distinct, etc.
    """
    query_class = DBQuery

    def convert_value_from_db(self, db_type, value):
        # Handle list types
        if db_type is not None and \
                isinstance(value, (list, tuple)) and len(value) and \
                db_type.startswith('ListField:'):
            db_sub_type = db_type.split(':', 1)[1]
            value = [self.convert_value_from_db(db_sub_type, subvalue)
                     for subvalue in value]
        else:
            value = db2python(db_type, value)
        return value

    # This gets called for each field type when you insert() an entity.
    # db_type is the string that you used in the DatabaseCreation mapping
    def convert_value_for_db(self, db_type, value):
        if db_type is not None and \
                isinstance(value, (list, tuple)) and len(value) and \
                db_type.startswith('ListField:'):
            db_sub_type = db_type.split(':', 1)[1]
            value = [self.convert_value_for_db(db_sub_type, subvalue)
                     for subvalue in value]
        else:
            value = python2db(db_type, value)
        return value

class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):
    @safe_call
    def insert(self, data, return_id=False):
        pk_column = self.query.get_meta().pk.column
        if pk_column in data:
            data['_id'] = data[pk_column]
            del data[pk_column]

        db_table = self.query.get_meta().db_table
        pk = self.connection.db_connection[db_table].save(data)
        return unicode(pk)

# TODO: Define a common nonrel API for updates and add it to the nonrel
# backend base classes and port this code to that API
class SQLUpdateCompiler(SQLCompiler):
    def execute_sql(self, return_id=False):
        """
        self.query - the data that should be inserted
        """
        dat = {}
        for (field, value), column in zip(self.query.values, self.query.columns):
            dat[column] = python2db(field.db_type(connection=self.connection), value)
        # every object should have a unique pk
        pk_field = self.query.model._meta.pk
        pk_name = pk_field.attname

        db_table = self.query.get_meta().db_table
        res = self.connection.db_connection[db_table].save(dat)
        return unicode(res)

class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass
