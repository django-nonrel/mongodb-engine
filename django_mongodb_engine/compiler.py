from functools import wraps
import re
import sys

from django.db.models import F, NOT_PROVIDED, AutoField, Field, FieldDoesNotExist, ForeignKey
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import MULTI
from django.db.models.sql.where import AND, OR
from django.db.utils import DatabaseError, IntegrityError
from django.utils.encoding import smart_str
from django.utils.tree import Node

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError
try:
    # ObjectId has been moved to bson.objectid in newer versions of PyMongo
    from bson.objectid import ObjectId, InvalidId
except ImportError:
    from pymongo.objectid import ObjectId, InvalidId

from djangotoolbox.db.basecompiler import (
    NonrelQuery,
    NonrelCompiler,
    NonrelInsertCompiler,
    NonrelUpdateCompiler,
    NonrelDeleteCompiler)
from djangotoolbox.fields import EmbeddedModelField, AbstractIterableField

from .aggregations import get_aggregation_class_by_name
from .query import A
from .utils import safe_regex, first


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
            raise IntegrityError, IntegrityError(smart_str(e)), sys.exc_info()[2]
        except PyMongoError, e:
            raise DatabaseError, DatabaseError(smart_str(e)), sys.exc_info()[2]
    return wrapper


def get_pk_column(duck):
    return duck.query.get_meta().pk.column


def _split_db_type(db_type):
    try:
        db_type, db_subtype = db_type.split(':', 1)
    except ValueError:
        db_subtype = None
    return db_type, db_subtype


class UpdateQueryMixin:
    def _setup_update(self, values):
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
        return spec, multi


class MongoQuery(NonrelQuery, UpdateQueryMixin):

    def __init__(self, compiler, fields):
        super(MongoQuery, self).__init__(compiler, fields)
        self.ordering = []
        self.collection = self.compiler.get_collection()
        self.mongo_query = getattr(compiler.query, 'raw_query', {})

    def __repr__(self):
        return '<MongoQuery: %r ORDER %r>' % (self.mongo_query, self.ordering)

    def fetch(self, low_mark, high_mark):
        # If this is a findAndModify query, do it on fetch.
        if getattr(self.query, "_modify_args", None):
            results = self.get_find_and_modify()
        else:
            results = self.get_cursor()
        pk_column = self.query.get_meta().pk.column
        for entity in results:
            entity[pk_column] = entity.pop('_id')
            yield entity

    @safe_call
    def count(self, limit=None):
        results = self.get_cursor()
        if limit is not None:
            results.limit(limit)
        return results.count()

    @safe_call
    def order_by(self, ordering):
        if isinstance(ordering, bool):
            # No need to add {$natural: ASCENDING} as it's the default.
            if not ordering:
                self.ordering.append(('$natural', DESCENDING))
        else:
            for field, ascending in ordering:
                column = '_id' if field.primary_key else field.column
                direction = ASCENDING if ascending else DESCENDING
                self.ordering.append((column, direction))

    @safe_call
    def delete(self):
        options = self.connection.operation_flags.get('delete', {})
        self.collection.remove(self.mongo_query, **options)

    def _get_query_fields(self):
        fields = None
        if self.query.select_fields and not self.query.aggregates:
            fields = [field.column for field in self.query.select_fields]
        return fields

    def get_find_and_modify(self):
        modify_args = getattr(self.query, "_modify_args", None)
        if modify_args:
            spec, multi = self._setup_update(modify_args)
            result = self.collection.find_and_modify(
                        query=self.mongo_query,
                        update=spec,
                        upsert=False,
                        sort=self.ordering or None,
                        full_response=False,
                        remove=False,
                        new=True,
                        fields=self._get_query_fields(),
            )
            return [result] if result else []

    def get_cursor(self):
        if self.query.low_mark == self.query.high_mark:
            return []

        fields = self._get_query_fields()
        cursor = self.collection.find(self.mongo_query, fields=fields)
        if self.ordering:
            cursor.sort(self.ordering)
        if self.query.low_mark > 0:
            cursor.skip(self.query.low_mark)
        if self.query.high_mark is not None:
            cursor.limit(int(self.query.high_mark - self.query.low_mark))
        return cursor

    # TODO get rid of global negated state
    def add_filters(self, filters):
        self.mongo_query = self._build_mongo_query(filters, self.mongo_query)

    def _build_mongo_query(self, filters, mongo_query=None):
        if filters.negated:
            self._negated = not self._negated

        if self._negated:
            connector = [AND, OR][filters.connector == AND]
        else:
            connector = filters.connector

        mongo_conditions = list(
            self._convert_filters(self._get_children(filters.children)))

        if filters.negated:
            self._negated = not self._negated

        if mongo_query:
            mongo_conditions.append(mongo_query)

        if not mongo_conditions:
            return {}

        if len(mongo_conditions) == 1:
            # {'$and|$or': [x]} <=> x
            return mongo_conditions[0]

        return {('$or' if connector == OR else '$and'): mongo_conditions}

    def _convert_filters(self, filters):
        for child in filters:
            if isinstance(child, Node):
                subquery = self._build_mongo_query(child)
                if subquery:
                    yield subquery
                continue

            # This block is all needed just to get db_type.
            # TODO: Investigate a better way
            constraint, lookup_type, annotation, value = child
            packed, value = constraint.process(lookup_type, value,
                                               self.connection)
            alias, column, db_type = packed

            field, lookup_type, value = self._decode_child(child)

            if lookup_type in ('month', 'day'):
                raise DatabaseError(
                    "MongoDB does not support month/day queries")
            if self._negated and lookup_type == 'range':
                raise DatabaseError(
                    "Negated range lookups are not supported")

            if column == get_pk_column(self):
                column = '_id'

            if isinstance(value, A):
                field = first(lambda field: field.column == column,
                              self.fields)
                column, value, lookup_type = self._process_A_object(
                                        field, value, lookup_type, annotation)

            if self._negated:
                if lookup_type in NEGATED_OPERATORS_MAP:
                    op_func = NEGATED_OPERATORS_MAP[lookup_type]
                else:
                    op_func = lambda val: {
                        '$not': OPERATORS_MAP[lookup_type](val)}
            else:
                op_func = OPERATORS_MAP[lookup_type]

            if lookup_type == 'isnull':
                lookup = op_func(value)
            else:
                lookup = op_func(self.convert_value_for_db(db_type, value))

            yield {column: lookup}

    def _process_A_object(self, field, value, lookup_type, annotation):
        """Process down into the A object Query to extract the correct types

        An A object can contain a deep query. This method attempts to parse
        that query a well as possible
        """
        column, value = value.as_q(field)
        # Check for an operator in the A. E.g. __contains
        split_column = column.split("__")
        if len(split_column) > 1:
            possible_op = split_column[-1]
            if possible_op in OPERATORS_MAP:
                # Reassemble without the operator
                column = "__".join(split_column[0:-1])
                lookup_type = possible_op

        # Recursive worker function
        # TODO: This algorithm is a little convoluted. Simplify
        def recurse_for_field_type(field_class, column_list):
            if not column_list:
                return field_class

            if isinstance(field_class, EmbeddedModelField):
                field_name = column_list[0]

                # If the embedded model is None, then this is a generic
                # EmbeddedModelField. We can only guess at the type.
                if field_class.embedded_model is None:
                    if field_name == "id":
                        return AutoField(primary_key=True)
                    else:
                        return Field()

                try:
                    field_class = field_class.embedded_model._meta\
                                         .get_field_by_name(field_name)[0]
                except FieldDoesNotExist:
                    # If this field is a ForeignKey, they may have appended
                    # '_id' to the end. Look for that and try again
                    if field_name.endswith("_id"):
                        field_name = field_name[:-3]
                        field_class = field_class.embedded_model._meta \
                                        .get_field_by_name(field_name)[0]

                        # We got a field, now let's make sure it is a ForeignKey
                        if not isinstance(field_class, ForeignKey):
                            raise
                return recurse_for_field_type(field_class, column_list[1:])

            # When searching for an Embedded model in a list, this will cast
            # the field to the appropriate type.
            elif isinstance(field_class, AbstractIterableField) and \
                    isinstance(field.item_field, EmbeddedModelField) and \
                    column_list[-1] == field.item_field.embedded_model\
                                                       ._meta.pk.attname:
                return AutoField(primary_key=True)

            elif isinstance(field_class, ForeignKey):
                # If we got here, it means this is not the last item in the
                # query, and it is a ForeignKey. That means they want a join.
                raise DatabaseError(
                    "ForeignKey joins are not supported. The query: '%s' will "
                    "fail." % ".".join([field_class.column] + column_list))
            else:
                # If we get here, that means the query continues beyond a known
                # field. E.g. Items in a DictField. We have to default to a
                # type, so we will use Field. If that behavior isn't
                # desired, stop your query at the known field.
                return Field()

        # In order for the query to be constructed correctly, some field-types
        # require value conversion. E.g. Decimal. This traverses the query
        # fields to get the correct type.
        field = recurse_for_field_type(field, column.split(".")[1:])
        value = self._normalize_lookup_value(lookup_type, value,
                                             field, annotation)

        # If the field type is ForeignKey, we need to replace the last field
        # of the column with the correct column name
        if isinstance(field, ForeignKey):
            if not column.endswith(field.column):
                items = column.split(".")
                items.pop()
                column = ".".join(items + [field.column])

        return column, value, lookup_type

    @safe_call # see #7
    def convert_value_for_db(self, db_type, value):
        if db_type is None or value is None:
            return value

        db_type, db_subtype = _split_db_type(db_type)
        if db_subtype is not None:
            if isinstance(value, (set, list, tuple)):
                # Sets are converted to lists here because MongoDB has no sets.
                return [self.convert_value_for_db(db_subtype, subvalue)
                        for subvalue in value]
            elif isinstance(value, dict):
                return dict(
                    (key, self.convert_value_for_db(db_subtype, subvalue))
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

class SQLCompiler(NonrelCompiler):
    """
    Base class for all Mongo compilers.
    """
    query_class = MongoQuery

    def get_collection(self):
        return self.connection.get_collection(self.query.get_meta().db_table)

    def execute_sql(self, result_type=MULTI):
        """
        Handles aggregate/count queries.
        """
        collection = self.get_collection()
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
                if lookup[0] != collection.name:
                    raise DatabaseError("Aggregations can not span multiple "
                                        "tables (tried %r and %r)." %
                                        (lookup[0], collection.name))
                lookup = lookup[1]
            self.query.aggregates[alias] = aggregate = aggregate_class(
                alias, lookup, aggregate.source)
            order.append(alias) # Just to keep the right order.
            initial.update(aggregate.initial())
            reduce.append(aggregate.reduce())
            finalize.append(aggregate.finalize())

        reduce = 'function(doc, out){ %s }' % '; '.join(reduce)
        finalize = 'function(out){ %s }' % '; '.join(finalize)
        cursor = collection.group(None, query.mongo_query, initial, reduce,
                                  finalize)

        ret = []
        for alias in order:
            result = cursor[0][alias] if alias else counts.pop(0)
            if result_type is MULTI:
                result = [result]
            ret.append(result)
        return ret


class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):

    @safe_call
    def insert(self, docs, return_id=False):
        """
        Stores a document using field columns as element names, except
        for the primary key field for which "_id" is used.

        If just a {pk_field: None} mapping is given a new empty
        document is created, otherwise value for a primary key may not
        be None.
        """
        for doc in docs:
            try:
                doc['_id'] = doc.pop(self.query.get_meta().pk.column)
            except KeyError:
                pass
            if doc.get('_id', NOT_PROVIDED) is None:
                if len(doc) == 1:
                    # insert with empty model
                    doc.clear()
                else:
                    raise DatabaseError("Can't save entity with _id set to None")

        collection = self.get_collection()
        options = self.connection.operation_flags.get('save', {})

        if return_id:
            return collection.save(doc, **options)
        else:
            collection.save(doc, **options)


# TODO: Define a common nonrel API for updates and add it to the nonrel
#       backend base classes and port this code to that API.
class SQLUpdateCompiler(NonrelUpdateCompiler, SQLCompiler, UpdateQueryMixin):
    query_class = MongoQuery

    def update(self, values):
        spec, multi = self._setup_update(values)
        return self.execute_update(spec, multi)

    @safe_call
    def execute_update(self, update_spec, multi=True, **kwargs):
        collection = self.get_collection()
        criteria = self.build_query().mongo_query
        options = self.connection.operation_flags.get('update', {})
        options = dict(options, **kwargs)
        info = collection.update(criteria, update_spec, multi=multi, **options)
        if info is not None:
            return info.get('n')


class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass
