import copy
import datetime
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.signals import connection_created

from pymongo.collection import Collection
from pymongo.connection import Connection

from djangotoolbox.db.base import \
    NonrelDatabaseClient, NonrelDatabaseFeatures, \
    NonrelDatabaseIntrospection, NonrelDatabaseOperations, \
    NonrelDatabaseValidation, NonrelDatabaseWrapper

from .creation import DatabaseCreation
from .utils import CollectionDebugWrapper


class DatabaseFeatures(NonrelDatabaseFeatures):
    supports_microsecond_precision = False
    string_based_auto_field = True
    supports_dicts = True
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

    def value_to_db_date(self, value):
        if value is None:
            return None
        return datetime.datetime(value.year, value.month, value.day)

    def value_to_db_time(self, value):
        if value is None:
            return None
        return datetime.datetime(1, 1, 1,
                                 value.hour, value.minute, value.second,
                                 value.microsecond)


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
