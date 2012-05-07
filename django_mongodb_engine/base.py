import copy
import datetime
import decimal
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.signals import connection_created
from django.db.utils import DatabaseError

from pymongo.collection import Collection
from pymongo.connection import Connection

# handle pymongo backward compatibility
try:
    from bson.objectid import ObjectId
    from bson.errors import InvalidId
except ImportError:
    from pymongo.objectid import ObjectId, InvalidId
    
from djangotoolbox.db.base import (
    NonrelDatabaseClient,
    NonrelDatabaseFeatures,
    NonrelDatabaseIntrospection,
    NonrelDatabaseOperations,
    NonrelDatabaseValidation,
    NonrelDatabaseWrapper)
from djangotoolbox.db.utils import decimal_to_string

from .creation import DatabaseCreation
from .utils import CollectionDebugWrapper


class DatabaseFeatures(NonrelDatabaseFeatures):
    supports_microsecond_precision = False
    supports_long_model_names = False


class DatabaseOperations(NonrelDatabaseOperations):
    compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    def max_name_length(self):
        return 254

    def check_aggregate_support(self, aggregate):
        import aggregations
        try:
            getattr(aggregations, aggregate.__class__.__name__)
        except AttributeError:
            raise NotImplementedError("django-mongodb-engine doesn't support "
                                      "%r aggregates." % type(aggregate))

    def sql_flush(self, style, tables, sequence_list):
        """
        Returns a list of SQL statements that have to be executed to
        drop all `tables`. No SQL in MongoDB, so just clear all tables
        here and return an empty list.
        """
        for table in tables:
            if table.startswith('system.'):
                # Do not try to drop system collections.
                continue
            self.connection.database[table].remove()
        return []

    def value_to_db_auto(self, value):
        """
        Mongo uses ObjectId-based AutoFields.
        """
        if value is None:
            return None
        return unicode(value)

    def _value_for_db(self, value, field, field_kind, db_type, lookup):
        """
        Allows parent to handle nonrel fields, convert AutoField
        keys to ObjectIds and date and times to datetimes.

        Let everything else pass to PyMongo -- when the value is used
        the driver will raise an exception if it got anything
        unacceptable.
        """
        if value is None:
            return None

        # Parent can handle iterable fields and Django wrappers.
        value = super(DatabaseOperations, self)._value_for_db(
            value, field, field_kind, db_type, lookup)

        # Convert decimals to strings preserving order.
        if field_kind == 'DecimalField':
            value = decimal_to_string(
                value, field.max_digits, field.decimal_places)

        # Anything with the "key" db_type is converted to an ObjectId.
        if db_type == 'key':
            try:
                return ObjectId(value)

            # Provide a better message for invalid IDs.
            except InvalidId:
                assert isinstance(value, unicode)
                if len(value) > 13:
                    value = value[:10] + '...'
                msg = "AutoField (default primary key) values must be " \
                      "strings representing an ObjectId on MongoDB (got " \
                      "%r instead)." % value
                if field.model._meta.db_table == 'django_site':
                    # Also provide some useful tips for (very common) issues
                    # with settings.SITE_ID.
                    msg += " Please make sure your SITE_ID contains a " \
                           "valid ObjectId string."
                raise DatabaseError(msg)

        # PyMongo can only process datatimes?
        elif db_type == 'date':
            return datetime.datetime(value.year, value.month, value.day)
        elif db_type == 'time':
            return datetime.datetime(1, 1, 1, value.hour, value.minute,
                                     value.second, value.microsecond)

        return value

    def _value_from_db(self, value, field, field_kind, db_type):
        """
        Deconverts keys, dates and times (also in collections).
        """

        # It is *crucial* that this is written as a direct check --
        # when value is an instance of serializer.LazyModelInstance
        # calling its __eq__ method does a database query.
        if value is None:
            return None

        # All keys have been turned into ObjectIds.
        if db_type == 'key':
            value = unicode(value)

        # We've converted dates and times to datetimes.
        elif db_type == 'date':
            value = datetime.date(value.year, value.month, value.day)
        elif db_type == 'time':
            value = datetime.time(value.hour, value.minute, value.second,
                                  value.microsecond)

        # Revert the decimal-to-string encoding.
        if field_kind == 'DecimalField':
            value = decimal.Decimal(value)

        return super(DatabaseOperations, self)._value_from_db(
            value, field, field_kind, db_type)


class DatabaseClient(NonrelDatabaseClient):
    pass


class DatabaseValidation(NonrelDatabaseValidation):
    pass


class DatabaseIntrospection(NonrelDatabaseIntrospection):

    def table_names(self):
        return self.connection.database.collection_names()

    def sequence_list(self):
        # Only required for backends that use integer primary keys.
        pass


class DatabaseWrapper(NonrelDatabaseWrapper):
    """
    Public API: connection, database, get_collection.
    """

    def __init__(self, *args, **kwargs):
        self.collection_class = kwargs.pop('collection_class', Collection)
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = DatabaseValidation(self)
        self.connected = False
        del self.connection

    def get_collection(self, name, **kwargs):
        if (kwargs.pop('existing', False) and
                name not in self.connection.database.collection_names()):
            return None
        collection = self.collection_class(self.database, name, **kwargs)
        if settings.DEBUG:
            collection = CollectionDebugWrapper(collection, self.alias)
        return collection

    def __getattr__(self, attr):
        if attr in ['connection', 'database']:
            assert not self.connected
            self._connect()
            return getattr(self, attr)
        raise AttributeError(attr)

    def _connect(self):
        settings = copy.deepcopy(self.settings_dict)

        def pop(name, default=None):
            return settings.pop(name) or default
        db_name = pop('NAME')
        host = pop('HOST')
        port = pop('PORT')
        user = pop('USER')
        password = pop('PASSWORD')
        options = pop('OPTIONS', {})

        self.operation_flags = options.pop('OPERATIONS', {})
        if not any(k in ['save', 'delete', 'update']
                   for k in self.operation_flags):
            # Flags apply to all operations.
            flags = self.operation_flags
            self.operation_flags = {'save': flags, 'delete': flags,
                                    'update': flags}

        # Lower-case all OPTIONS keys.
        for key in options.iterkeys():
            options[key.lower()] = options.pop(key)

        try:
            self.connection = Connection(host=host, port=port, **options)
            self.database = self.connection[db_name]
        except TypeError:
            exc_info = sys.exc_info()
            raise ImproperlyConfigured, exc_info[1], exc_info[2]

        if user and password:
            if not self.database.authenticate(user, password):
                raise ImproperlyConfigured("Invalid username or password.")

        if settings.get('MONGODB_AUTOMATIC_REFERENCING'):
            from .serializer import TransformDjango
            self.database.add_son_manipulator(TransformDjango())

        self.connected = True
        connection_created.send(sender=self.__class__, connection=self)

    def _reconnect(self):
        if self.connected:
            del self.connection
            del self.database
            self.connected = False
        self._connect()

    def _commit(self):
        pass

    def _rollback(self):
        pass

    def close(self):
        pass
