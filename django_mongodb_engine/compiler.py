from future_builtins import zip
import sys
import re

from datetime import datetime
from functools import wraps

from django.db.utils import DatabaseError
from django.db.models.fields import NOT_PROVIDED

import pymongo
from pymongo.objectid import ObjectId

from djangotoolbox.db.basecompiler import NonrelQuery, NonrelCompiler, \
    NonrelInsertCompiler, NonrelUpdateCompiler, NonrelDeleteCompiler


OPERATORS_MAP = {
    'exact':    lambda val: val,
    'iexact':    lambda val: re.compile(r'^%s$' % val, re.IGNORECASE),
    'startswith':    lambda val: re.compile(r'^%s' % val),
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

    @safe_generator
    def fetch(self, low_mark, high_mark):
        results = self._get_results()
        if low_mark > 0:
            results = results.skip(low_mark)
        if high_mark is not None:
            results = results.limit(high_mark - low_mark)

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
        return results

class SQLCompiler(NonrelCompiler):
    """
    A simple query: no joins, no distinct, etc.
    """
    query_class = DBQuery

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

        if value in (None, NOT_PROVIDED):
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

    def _save(self, data, return_id=False):
        connection = self.connection.db_connection
        db_table = self.query.get_meta().db_table
        primary_key = connection[db_table].save(data, **self.insert_params())
        return unicode(primary_key)


class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):
    @safe_call
    def insert(self, data, return_id=False):
        pk_column = self.query.get_meta().pk.column
        try:
            data['_id'] = data.pop(pk_column)
        except KeyError:
            pass
        return SQLCompiler._save(self, data, return_id)

# TODO: Define a common nonrel API for updates and add it to the nonrel
# backend base classes and port this code to that API
class SQLUpdateCompiler(SQLCompiler):
    @safe_call
    def execute_sql(self, return_id=False):
        # self.query: the data that shall be inserted
        data = {}
        for (field, value), column in zip(self.query.values, self.query.columns):
            data[column] = python2db(field.db_type(connection=self.connection), value)
        return super(SQLCompiler, self)._save(data, return_id)

class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass
