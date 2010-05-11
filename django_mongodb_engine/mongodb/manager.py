from django.db import connections
from django.db.models.manager import Manager as DJManager

import pymongo
from pymongo.objectid import ObjectId

import re
import copy
from .utils import dict_keys_to_str
try:
    from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
except ImportError:
    class ObjectDoesNotExist(Exception):
        pass
    class MultipleObjectsReturned(Exception):
        pass
    
from django_mongodb_engine.mongodb.mongodb_serializer import TransformDjango

DoesNotExist = ObjectDoesNotExist

__all__ = ['queryset_manager', 'Q', 'InvalidQueryError',
           'InvalidCollectionError']

# The maximum number of items to display in a QuerySet.__repr__
REPR_OUTPUT_SIZE = 20

class InvalidQueryError(Exception):
    pass


class OperationError(Exception):
    pass

class InvalidCollectionError(Exception):
    pass

DoesNotExist = ObjectDoesNotExist
RE_TYPE = type(re.compile(''))


class Q(object):

    OR = '||'
    AND = '&&'
    OPERATORS = {
        'eq': 'this.%(field)s == %(value)s',
        'ne': 'this.%(field)s != %(value)s',
        'gt': 'this.%(field)s > %(value)s',
        'gte': 'this.%(field)s >= %(value)s',
        'lt': 'this.%(field)s < %(value)s',
        'lte': 'this.%(field)s <= %(value)s',
        'lte': 'this.%(field)s <= %(value)s',
        'in': '%(value)s.indexOf(this.%(field)s) != -1',
        'nin': '%(value)s.indexOf(this.%(field)s) == -1',
        'mod': '%(field)s %% %(value)s',
        'all': ('%(value)s.every(function(a){'
                'return this.%(field)s.indexOf(a) != -1 })'),
        'size': 'this.%(field)s.length == %(value)s',
        'exists': 'this.%(field)s != null',
        'regex_eq': '%(value)s.test(this.%(field)s)',
        'regex_ne': '!%(value)s.test(this.%(field)s)',
    }

    def __init__(self, **query):
        self.query = [query]

    def _combine(self, other, op):
        obj = Q()
        obj.query = ['('] + copy.deepcopy(self.query) + [op]
        obj.query += copy.deepcopy(other.query) + [')']
        return obj

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __and__(self, other):
        return self._combine(other, self.AND)

    def as_js(self, document):
        js = []
        js_scope = {}
        for i, item in enumerate(self.query):
            if isinstance(item, dict):
                item_query = QuerySet._transform_query(document, **item)
                # item_query will values will either be a value or a dict
                js.append(self._item_query_as_js(item_query, js_scope, i))
            else:
                js.append(item)
        return pymongo.code.Code(' '.join(js), js_scope)

    def _item_query_as_js(self, item_query, js_scope, item_num):
        # item_query will be in one of the following forms
        #    {'age': 25, 'name': 'Test'}
        #    {'age': {'$lt': 25}, 'name': {'$in': ['Test', 'Example']}
        #    {'age': {'$lt': 25, '$gt': 18}}
        js = []
        for i, (key, value) in enumerate(item_query.items()):
            op = 'eq'
            # Construct a variable name for the value in the JS
            value_name = 'i%sf%s' % (item_num, i)
            if isinstance(value, dict):
                # Multiple operators for this field
                for j, (op, value) in enumerate(value.items()):
                    # Create a custom variable name for this operator
                    op_value_name = '%so%s' % (value_name, j)
                    # Construct the JS that uses this op
                    value, operation_js = self._build_op_js(op, key, value,
                                                            op_value_name)
                    # Update the js scope with the value for this op
                    js_scope[op_value_name] = value
                    js.append(operation_js)
            else:
                # Construct the JS for this field
                value, field_js = self._build_op_js(op, key, value, value_name)
                js_scope[value_name] = value
                js.append(field_js)
        return ' && '.join(js)

    def _build_op_js(self, op, key, value, value_name):
        """Substitute the values in to the correct chunk of Javascript.
        """
        if isinstance(value, RE_TYPE):
            # Regexes are handled specially
            if op.strip('$') == 'ne':
                op_js = Q.OPERATORS['regex_ne']
            else:
                op_js = Q.OPERATORS['regex_eq']
        else:
            op_js = Q.OPERATORS[op.strip('$')]

        # Comparing two ObjectIds in Javascript doesn't work..
        if isinstance(value, pymongo.objectid.ObjectId):
            value = unicode(value)

        # Perform the substitution
        operation_js = op_js % {
            'field': key, 
            'value': value_name
        }
        return value, operation_js

class InternalMetadata:
    def __init__(self, meta):
        self.object_name  = meta["object_name"]

class InternalModel:
    """
    An internal queryset model to be embedded in a query set for django compatibility.
    """
    def __init__(self, document):
        self.document = document
        self._meta = InternalMetadata(document._meta)
        self.DoesNotExist = ObjectDoesNotExist

class QuerySet(object):
    """A set of results returned from a query. Wraps a MongoDB cursor,
    providing :class:`~mongoengine.Document` objects as the results.
    """

    def __init__(self, document, collection):
        self._document = document
        self._collection_obj = collection
        self._accessed_collection = False
        self._query = {}
        self._where_clause = None
        self._loaded_fields = []
        self._ordering = []
        self.transform = TransformDjango()
        
        # If inheritance is allowed, only return instances and instances of
        # subclasses of the class being used
        #if document._meta.get('allow_inheritance'):
            #self._query = {'_types': self._document._class_name}
        self._cursor_obj = None
        self._limit = None
        self._skip = None

        #required for compatibility with django
        #self.model = InternalModel(document)

    def __call__(self, q_obj=None, **query):
        """Filter the selected documents by calling the
        :class:`~mongoengine.queryset.QuerySet` with a query.

        :param q_obj: a :class:`~mongoengine.queryset.Q` object to be used in
            the query; the :class:`~mongoengine.queryset.QuerySet` is filtered
            multiple times with different :class:`~mongoengine.queryset.Q`
            objects, only the last one will be used
        :param query: Django-style query keyword arguments
        """
        if q_obj:
            self._where_clause = q_obj.as_js(self._document)
        query = QuerySet._transform_query(_doc_cls=self._document, **query)
        self._query.update(query)
        return self

    def filter(self, *q_objs, **query):
        """An alias of :meth:`~mongoengine.queryset.QuerySet.__call__`
        """
        return self.__call__(*q_objs, **query)

    def find(self, query):
        self._query.update(self.transform.transform_incoming(query, self._collection))
        return self

    def exclude(self, *q_objs, **query):
        """An alias of :meth:`~mongoengine.queryset.QuerySet.__call__`
        """
        query["not"] = True
        return self.__call__(*q_objs, **query)

    def all(self):
        """An alias of :meth:`~mongoengine.queryset.QuerySet.__call__`
        """
        return self.__call__()
    
    def distinct(self, *args, **kwargs):
        """
        Distinct method
        """
        return self._cursor.distinct(*args, **kwargs)

    @property
    def _collection(self):
        """Property that returns the collection object. This allows us to
        perform operations only if the collection is accessed.
        """
        return self._collection_obj
    
    def values(self, *args):
        return (args and [dict(zip(args,[getattr(doc, key) for key in args])) for doc in self]) or [obj for obj in self._cursor.clone()]
        
    def values_list(self, *args, **kwargs):
        flat = kwargs.pop("flat", False)
        if flat and len(args) != 1:
            raise Exception("args len must be 1 when flat=True")
        
        return (flat and self.distinct(args[0] if not args[0] in ["id", "pk"] else "_id")) or zip(*[self.distinct(field if not field in ["id", "pk"] else "_id") for field in args])
#                
#            if self._document._meta['geo_indexes'] and \
#               pymongo.version >= "1.5.1":
#                from pymongo import GEO2D
#                for index in self._document._meta['geo_indexes']:
#                    self._collection.ensure_index([(index, GEO2D)])
#            
#            # Ensure all needed field indexes are created
#            for field_name, field_instance in self._document._fields.iteritems():
#                if field_instance.__class__.__name__ == 'GeoLocationField':
#                    self._collection.ensure_index([(field_name, pymongo.GEO2D),])
#        return self._collection_obj

    @property
    def _cursor(self):
        if self._cursor_obj is None:
            cursor_args = {}
            if self._loaded_fields:
                cursor_args = {'fields': self._loaded_fields}
            self._cursor_obj = self._collection.find(self._query, 
                                                     **cursor_args)
            # Apply where clauses to cursor
            if self._where_clause:
                self._cursor_obj.where(self._where_clause)

            # apply default ordering
#            if self._document._meta['ordering']:
#                self.order_by(*self._document._meta['ordering'])

        return self._cursor_obj.clone()

    @classmethod
    def _lookup_field(cls, document, fields):
        """
        Looks for "field" in "document"
        """
        if isinstance(fields, (tuple, list)):
            return [document._meta.get_field_by_name((field == "pk" and "id") or field)[0] for field in fields]
        return document._meta.get_field_by_name((fields == "pk" and "id") or fields)[0]

    @classmethod
    def _translate_field_name(cls, doc_cls, field, sep='.'):
        """Translate a field attribute name to a database field name.
        """
        parts = field.split(sep)
        parts = [f.attname for f in QuerySet._lookup_field(doc_cls, parts)]
        return '.'.join(parts)

    @classmethod
    def _transform_query(self,  _doc_cls=None, **parameters):
        """
        Converts parameters to mongodb queries. 
        """
        spec = {}
        operators = ['ne', 'gt', 'gte', 'lt', 'lte', 'in', 'nin', 'mod', 'all', 'size', 'exists']
        match_operators = ['contains', 'icontains', 'startswith', 'istartswith', 'endswith', 'iendswith', 'exact', 'iexact']
        exclude = parameters.pop("not", False)
        
        for key, value in parameters.items():
            
            
            parts  = key.split("__")
            lookup_type = (len(parts)>=2) and ( parts[-1] in operators + match_operators and parts.pop()) or ""
            
            # Let's get the right field and be sure that it exists
            parts[0] = QuerySet._lookup_field(_doc_cls, parts[0]).attname
            
            if not lookup_type and len(parts)==1:
                if exclude:
                    value = {"$ne" : value}
                spec.update({parts[0] : value})
                continue
            
            if parts[0] == "id":
                parts[0] = "_id"
                value = [isinstance(par, basestring) and ObjectId(par) or par for par in value]
                
            if lookup_type in ['contains', 'icontains',
                                 'startswith', 'istartswith',
                                 'endswith', 'iendswith',
                                 'exact', 'iexact']:
                flags = 0
                if lookup_type.startswith('i'):
                    flags = re.IGNORECASE
                    lookup_type = lookup_type.lstrip('i')
                    
                regex = r'%s'
                if lookup_type == 'startswith':
                    regex = r'^%s'
                elif lookup_type == 'endswith':
                    regex = r'%s$'
                elif lookup_type == 'exact':
                    regex = r'^%s$'
                    
                value = re.compile(regex % value, flags)
                
            elif lookup_type in operators:
                value = { "$" + lookup_type : value}
            elif lookup_type and len(parts)==1:
                raise DatabaseError("Unsupported lookup type: %r" % lookup_type)
    
            key = '.'.join(parts)
            if exclude:
                value = {"$ne" : value}
            spec.update({key : value})
            
        return spec
    
    def get(self, *q_objs, **query):
        """Retrieve the the matching object raising id django is available
        :class:`~django.core.exceptions.MultipleObjectsReturned` or
        :class:`~django.core.exceptions.ObjectDoesNotExist` exceptions if multiple or
        no results are found.
        If django is not available:
        :class:`~mongoengine.queryset.MultipleObjectsReturned` or
        `DocumentName.MultipleObjectsReturned` exception if multiple results and
        :class:`~mongoengine.queryset.DoesNotExist` or `DocumentName.DoesNotExist`
        if no results are found.

        .. versionadded:: 0.3
        """
        self.__call__(*q_objs, **query)
        count = self.count()
        if count == 1:
            return self[0]
        elif count > 1:
            message = u'%d items returned, instead of 1' % count
            raise self._document.MultipleObjectsReturned(message)
        else:
            raise self._document.DoesNotExist("%s matching query does not exist."
                                              % self._document._meta.object_name)

    def get_or_create(self, *q_objs, **query):
        """Retrieve unique object or create, if it doesn't exist. Returns a tuple of 
        ``(object, created)``, where ``object`` is the retrieved or created object 
        and ``created`` is a boolean specifying whether a new object was created. Raises
        :class:`~mongoengine.queryset.MultipleObjectsReturned` or
        `DocumentName.MultipleObjectsReturned` if multiple results are found.
        A new document will be created if the document doesn't exists; a
        dictionary of default values for the new document may be provided as a
        keyword argument called :attr:`defaults`.

        .. versionadded:: 0.3
        """
        defaults = query.get('defaults', {})
        if 'defaults' in query:
            del query['defaults']

        self.__call__(*q_objs, **query)
        count = self.count()
        if count == 0:
            query.update(defaults)
            doc = self._document(**query)
            doc.save()
            return doc, True
        elif count == 1:
            return self.first(), False
        else:
            message = u'%d items returned, instead of 1' % count
            raise self._document.MultipleObjectsReturned(message)

    def first(self):
        """Retrieve the first object matching the query.
        """
        try:
            result = self[0]
        except IndexError:
            result = None
        return result

    def with_id(self, object_id):
        """Retrieve the object matching the id provided.

        :param object_id: the value for the id of the document to look up
        """
        id_field = self._document._meta['id_field']
        object_id = self._document._fields[id_field].to_mongo(object_id)

        result = self._collection.find_one({'_id': (not isinstance(object_id, ObjectId) and ObjectId(object_id)) or object_id})
        if result is not None:
            result = self._document(**dict_keys_to_str(result))
        return result

    def in_bulk(self, object_ids):
        """Retrieve a set of documents by their ids.
        
        :param object_ids: a list or tuple of ``ObjectId``\ s
        :rtype: dict of ObjectIds as keys and collection-specific
                Document subclasses as values.

        .. versionadded:: 0.3
        """
        doc_map = {}

        docs = self._collection.find({'_id': {'$in': [ (not isinstance(id, ObjectId) and ObjectId(id)) or id for id in object_ids]}})
        for doc in docs:
            doc_map[str(doc['id'])] = self._document(**dict_keys_to_str(doc))
 
        return doc_map
    
    def count(self):
        """Count the selected elements in the query.
        """
        if self._limit == 0:
            return 0
        return self._cursor.count(with_limit_and_skip=False)

    def __len__(self):
        return self.count()

    def map_reduce(self, map_f, reduce_f, finalize_f=None, limit=None,
                   scope=None, keep_temp=False):
        """Perform a map/reduce query using the current query spec
        and ordering. While ``map_reduce`` respects ``QuerySet`` chaining,
        it must be the last call made, as it does not return a maleable
        ``QuerySet``.

        See the :meth:`~mongoengine.tests.QuerySetTest.test_map_reduce`
        and :meth:`~mongoengine.tests.QuerySetTest.test_map_advanced`
        tests in ``tests.queryset.QuerySetTest`` for usage examples.

        :param map_f: map function, as :class:`~pymongo.code.Code` or string
        :param reduce_f: reduce function, as
                         :class:`~pymongo.code.Code` or string
        :param finalize_f: finalize function, an optional function that
                           performs any post-reduction processing.
        :param scope: values to insert into map/reduce global scope. Optional.
        :param limit: number of objects from current query to provide
                      to map/reduce method
        :param keep_temp: keep temporary table (boolean, default ``True``)

        Returns an iterator yielding
        :class:`~mongoengine.document.MapReduceDocument`.

        .. note:: Map/Reduce requires server version **>= 1.1.1**. The PyMongo
           :meth:`~pymongo.collection.Collection.map_reduce` helper requires
           PyMongo version **>= 1.2**.

        .. versionadded:: 0.3
        """
        #from document import MapReduceDocument
        
        if not hasattr(self._collection, "map_reduce"):
            raise NotImplementedError("Requires MongoDB >= 1.1.1")

        map_f_scope = {}
        if isinstance(map_f, pymongo.code.Code):
            map_f_scope = map_f.scope
            map_f = unicode(map_f)
#        map_f = pymongo.code.Code(self._sub_js_fields(map_f), map_f_scope)
        map_f = pymongo.code.Code(map_f, map_f_scope)

        reduce_f_scope = {}
        if isinstance(reduce_f, pymongo.code.Code):
            reduce_f_scope = reduce_f.scope
            reduce_f = unicode(reduce_f)
#        reduce_f_code = self._sub_js_fields(reduce_f)
        reduce_f_code = reduce_f
        reduce_f = pymongo.code.Code(reduce_f_code, reduce_f_scope)

        mr_args = {'query': self._query, 'keeptemp': keep_temp}

        if finalize_f:
            finalize_f_scope = {}
            if isinstance(finalize_f, pymongo.code.Code):
                finalize_f_scope = finalize_f.scope
                finalize_f = unicode(finalize_f)
#            finalize_f_code = self._sub_js_fields(finalize_f)
            finalize_f_code = finalize_f
            finalize_f = pymongo.code.Code(finalize_f_code, finalize_f_scope)
            mr_args['finalize'] = finalize_f

        if scope:
            mr_args['scope'] = scope

        if limit:
            mr_args['limit'] = limit

        results = self._collection.map_reduce(map_f, reduce_f, **mr_args)
        results = results.find()

        if self._ordering:
            results = results.sort(self._ordering)

        for doc in results:
            yield self._document.objects.with_id(doc['value'])

    def limit(self, n):
        """Limit the number of returned documents to `n`. This may also be
        achieved using array-slicing syntax (e.g. ``User.objects[:5]``).

        :param n: the maximum number of objects to return
        """
        if n == 0:
            self._cursor.limit(1)
        else:
            self._cursor.limit(n)
        self._limit = n

        # Return self to allow chaining
        return self

    def skip(self, n):
        """Skip `n` documents before returning the results. This may also be
        achieved using array-slicing syntax (e.g. ``User.objects[5:]``).

        :param n: the number of objects to skip before returning results
        """
        self._cursor.skip(n)
        self._skip = n
        return self

    def __getitem__(self, key):
        """Support skip and limit using getitem and slicing syntax.
        """
        # Slice provided
        if isinstance(key, slice):
            try:
                self._cursor_obj = self._cursor[key]
                self._skip, self._limit = key.start, key.stop
            except IndexError, err:
                # PyMongo raises an error if key.start == key.stop, catch it,
                # bin it, kill it. 
                start = key.start or 0
                if start >= 0 and key.stop >= 0 and key.step is None:
                    if start == key.stop:
                        self.limit(0)
                        self._skip, self._limit = key.start, key.stop - start
                        return self
                raise err
            # Allow further QuerySet modifications to be performed
            return self
        # Integer index provided
        elif isinstance(key, int):
            return self._document(**dict_keys_to_str(self._cursor[key]))

    def only(self, *fields):
        """Load only a subset of this document's fields. ::
        
            post = BlogPost.objects(...).only("title")
        
        :param fields: fields to include

        .. versionadded:: 0.3
        """
        self._loaded_fields = []
        for field in fields:
            if '.' in field:
                raise InvalidQueryError('Subfields cannot be used as '
                                        'arguments to QuerySet.only')
            # Translate field name
            field = QuerySet._lookup_field(self._document, field)[-1].db_field
            self._loaded_fields.append(field)

        # _cls is needed for polymorphism
        if self._document._meta.get('allow_inheritance'):
            self._loaded_fields += ['_cls']
        return self

    def order_by(self, *args):
        """Order the :class:`~mongoengine.queryset.QuerySet` by the keys. The
        order may be specified by prepending each of the keys by a + or a -.
        Ascending order is assumed.

        :param keys: fields to order the query results by; keys may be
            prefixed with **+** or **-** to determine the ordering direction
        """
        
        self._ordering = {}
        for col in args:
            self._ordering.update({ (col.startswith("-") and col[1:]) or col : (col.startswith("-") and -1) or 1 })
            
        self._cursor.sort(self._ordering)
        return self

    def explain(self, format=False):
        """Return an explain plan record for the
        :class:`~mongoengine.queryset.QuerySet`\ 's cursor.

        :param format: format the plan before returning it
        """

        plan = self._cursor.explain()
        if format:
            import pprint
            plan = pprint.pformat(plan)
        return plan

    def delete(self, safe=False):
        """Delete the documents matched by the query.

        :param safe: check if the operation succeeded before returning
        """
        self._collection.remove(self._query, safe=safe)

    @classmethod
    def _transform_update(cls, _doc_cls=None, **update):
        """Transform an update spec from Django-style format to Mongo format.
        """
        operators = ['set', 'unset', 'inc', 'dec', 'push', 'push_all', 'pull',
                     'pull_all']

        mongo_update = {}
        for key, value in update.items():
            parts = key.split('__')
            # Check for an operator and transform to mongo-style if there is
            op = None
            if parts[0] in operators:
                op = parts.pop(0)
                # Convert Pythonic names to Mongo equivalents
                if op in ('push_all', 'pull_all'):
                    op = op.replace('_all', 'All')
                elif op == 'dec':
                    # Support decrement by flipping a positive value's sign
                    # and using 'inc'
                    op = 'inc'
                    if value > 0:
                        value = -value

            if _doc_cls:
                # Switch field names to proper names [set in Field(name='foo')]
                fields = QuerySet._lookup_field(_doc_cls, parts)
                parts = [field.db_field for field in fields]

                # Convert value to proper value
                field = fields[-1]
                if op in (None, 'set', 'unset', 'push', 'pull'):
                    value = field.prepare_query_value(op, value)
                elif op in ('pushAll', 'pullAll'):
                    value = [field.prepare_query_value(op, v) for v in value]

            key = '.'.join(parts)

            if op:
                value = {key: value}
                key = '$' + op

            if op is None or key not in mongo_update:
                mongo_update[key] = value
            elif key in mongo_update and isinstance(mongo_update[key], dict):
                mongo_update[key].update(value)

        return mongo_update

    def update(self, safe_update=True, upsert=False, **update):
        """Perform an atomic update on the fields matched by the query.

        :param safe: check if the operation succeeded before returning
        :param update: Django-style update keyword arguments

        .. versionadded:: 0.2
        """
        if pymongo.version < '1.1.1':
            raise OperationError('update() method requires PyMongo 1.1.1+')

        update = QuerySet._transform_update(self._document, **update)
        try:
            self._collection.update(self._query, update, safe=safe_update, 
                                    upsert=upsert, multi=True)
        except pymongo.errors.OperationFailure, err:
            if unicode(err) == u'multi not coded yet':
                message = u'update() method requires MongoDB 1.1.3+'
                raise OperationError(message)
            raise OperationError(u'Update failed (%s)' % unicode(err))

    def update_one(self, safe_update=True, upsert=False, **update):
        """Perform an atomic update on first field matched by the query.

        :param safe: check if the operation succeeded before returning
        :param update: Django-style update keyword arguments

        .. versionadded:: 0.2
        """
        update = QuerySet._transform_update(self._document, **update)
        try:
            # Explicitly provide 'multi=False' to newer versions of PyMongo
            # as the default may change to 'True'
            if pymongo.version >= '1.1.1':
                self._collection.update(self._query, update, safe=safe_update, 
                                        upsert=upsert, multi=False)
            else:
                # Older versions of PyMongo don't support 'multi'
                self._collection.update(self._query, update, safe=safe_update)
        except pymongo.errors.OperationFailure, e:
            raise OperationError(u'Update failed [%s]' % unicode(e))

    def __iter__(self, *args, **kwargs):
        for obj in self._cursor:
            yield self._document(**dict_keys_to_str(obj))

    def _sub_js_fields(self, code):
        """When fields are specified with [~fieldname] syntax, where 
        *fieldname* is the Python name of a field, *fieldname* will be 
        substituted for the MongoDB name of the field (specified using the
        :attr:`name` keyword argument in a field's constructor).
        """
        def field_sub(match):
            # Extract just the field name, and look up the field objects
            field_name = match.group(1).split('.')
            fields = QuerySet._lookup_field(self._document, field_name)
            # Substitute the correct name for the field into the javascript
            return u'["%s"]' % fields[-1].db_field

        return re.sub(u'\[\s*~([A-z_][A-z_0-9.]+?)\s*\]', field_sub, code)

    def exec_js(self, code, *fields, **options):
        """
        Execute a Javascript function on the server. A list of fields may be
        provided, which will be translated to their correct names and supplied
        as the arguments to the function. A few extra variables are added to
        the function's scope: ``collection``, which is the name of the
        collection in use; ``query``, which is an object representing the
        current query; and ``options``, which is an object containing any
        options specified as keyword arguments.

        As fields in MongoEngine may use different names in the database (set
        using the :attr:`db_field` keyword argument to a :class:`Field` 
        constructor), a mechanism exists for replacing MongoEngine field names
        with the database field names in Javascript code. When accessing a 
        field, use square-bracket notation, and prefix the MongoEngine field
        name with a tilde (~).

        :param code: a string of Javascript code to execute
        :param fields: fields that you will be using in your function, which
            will be passed in to your function as arguments
        :param options: options that you want available to the function
            (accessed in Javascript through the ``options`` object)
        """
#        code = self._sub_js_fields(code)

        fields = [QuerySet._translate_field_name(self._document, f) for f in fields]
        collection = self._collection

        scope = {
            'collection': collection.name,
            'options': options or {},
        }

        query = self._query
        if self._where_clause:
            query['$where'] = self._where_clause

        scope['query'] = query
        code = pymongo.code.Code(code, scope=scope)

        return collection.database.eval(code, *fields)

    def sum(self, field):
        """Sum over the values of the specified field.

        :param field: the field to sum over; use dot-notation to refer to
            embedded document fields
        """
        sum_func = """
            function(sumField) {
                var total = 0.0;
                db[collection].find(query).forEach(function(doc) {
                    total += (doc[sumField] || 0.0);
                });
                return total;
            }
        """
        return self.exec_js(sum_func, field)

    def average(self, field):
        """Average over the values of the specified field.

        :param field: the field to average over; use dot-notation to refer to
            embedded document fields
        """
        average_func = """
            function(averageField) {
                var total = 0.0;
                var num = 0;
                db[collection].find(query).forEach(function(doc) {
                    if (doc[averageField]) {
                        total += doc[averageField];
                        num += 1;
                    }
                });
                return total / num;
            }
        """
        return self.exec_js(average_func, field)

    def item_frequencies(self, list_field, normalize=False):
        """Returns a dictionary of all items present in a list field across
        the whole queried set of documents, and their corresponding frequency.
        This is useful for generating tag clouds, or searching documents.

        :param list_field: the list field to use
        :param normalize: normalize the results so they add to 1.0
        """
        freq_func = """
            function(listField) {
                if (options.normalize) {
                    var total = 0.0;
                    db[collection].find(query).forEach(function(doc) {
                        total += doc[listField].length;
                    });
                }

                var frequencies = {};
                var inc = 1.0;
                if (options.normalize) {
                    inc /= total;
                }
                db[collection].find(query).forEach(function(doc) {
                    doc[listField].forEach(function(item) {
                        frequencies[item] = inc + (frequencies[item] || 0);
                    });
                });
                return frequencies;
            }
        """
        return self.exec_js(freq_func, list_field, normalize=normalize)

    def __repr__(self):
        limit = REPR_OUTPUT_SIZE + 1
        if self._limit is not None and self._limit < limit:
            limit = self._limit
        data = list(self[self._skip:limit])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)


class Manager(DJManager):

    def __init__(self, manager_func=None):
        super(Manager, self).__init__()
        self._manager_func = manager_func
        self._collection = None

    def contribute_to_class(self, model, name):
        # TODO: Use weakref because of possible memory leak / circular reference.
        self.model = model
#        setattr(model, name, ManagerDescriptor(self))
        if model._meta.abstract or (self._inherited and not self.model._meta.proxy):
            model._meta.abstract_managers.append((self.creation_counter, name,
                    self))
        else:
            model._meta.concrete_managers.append((self.creation_counter, name,
                self))
            
    def __get__(self, instance, owner):
        """Descriptor for instantiating a new QuerySet object when
        Document.objects is accessed.
        """
        self.model = owner #We need to set the model to get the db

        if instance is not None:
            # Document class being used rather than a document object
            return self

        if self._collection is None:
            self._collection = connections[self.db].db_connection[owner._meta.db_table]

        # owner is the document that contains the QuerySetManager
        queryset = QuerySet(owner, self._collection)
        if self._manager_func:
            if self._manager_func.func_code.co_argcount == 1:
                queryset = self._manager_func(queryset)
            else:
                queryset = self._manager_func(owner, queryset)
        return queryset


def queryset_manager(func):
    """Decorator that allows you to define custom QuerySet managers on
    :class:`~mongoengine.Document` classes. The manager must be a function that
    accepts a :class:`~mongoengine.Document` class as its first argument, and a
    :class:`~mongoengine.queryset.QuerySet` as its second argument. The method
    function should return a :class:`~mongoengine.queryset.QuerySet`, probably
    the same one that was passed in, but modified in some way.
    """
    if func.func_code.co_argcount == 1:
        import warnings
        msg = 'Methods decorated with queryset_manager should take 2 arguments'
        warnings.warn(msg, DeprecationWarning)
    return QuerySetManager(func)
