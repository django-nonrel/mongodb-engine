from django.core.exceptions import ImproperlyConfigured
from django.db.backends.signals import connection_created
from django.conf import settings
from django.utils.functional import wraps

import pymongo
from .creation import DatabaseCreation
from .client import DatabaseClient
from .utils import CollectionDebugWrapper

from djangotoolbox.db.base import (
    NonrelDatabaseFeatures,
    NonrelDatabaseWrapper,
    NonrelDatabaseValidation,
    NonrelDatabaseIntrospection,
    NonrelDatabaseOperations
)

from datetime import datetime

class ImproperlyConfiguredWarning(Warning):
    pass

class DatabaseFeatures(NonrelDatabaseFeatures):
    string_based_auto_field = True
    supports_dicts = True

class DatabaseOperations(NonrelDatabaseOperations):
    compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    def max_name_length(self):
        return 254

    def check_aggregate_support(self, aggregate):
        import aggregations
        try:
            getattr(aggregations, aggregate.__class__.__name__)
        except AttributeError:
            raise NotImplementedError("django-mongodb-engine does not support %r "
                                      "aggregates" % type(aggregate))

    def sql_flush(self, style, tables, sequence_list):
        """
        Returns a list of SQL statements that have to be executed to drop
        all `tables`. No SQL in MongoDB, so just drop all tables here and
        return an empty list.
        """
        tables = self.connection.db.collection_names()
        for table in tables:
            if table.startswith('system.'):
                # no do not system collections
                continue
            self.connection.db.drop_collection(table)
        return []

    def value_to_db_date(self, value):
        if value is None:
            return None
        return datetime(value.year, value.month, value.day)

    def value_to_db_time(self, value):
        if value is None:
            return None
        return datetime(1, 1, 1, value.hour, value.minute, value.second,
                                 value.microsecond)

class DatabaseValidation(NonrelDatabaseValidation):
    pass

class DatabaseIntrospection(NonrelDatabaseIntrospection):
    def table_names(self):
        return self.connection.collection_names()

    def sequence_list(self):
        # Only required for backends that support ManyToMany relations
        pass

def requires_connection(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self._connected:
            self._connect()
        return method(self, *args, **kwargs)
    return wrapper

class DatabaseWrapper(NonrelDatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = DatabaseValidation(self)

        self._connected = False
        self.safe_inserts = False
        self.wait_for_slaves = 0

    @requires_connection
    def get_collection(self, name, **kwargs):
        collection = pymongo.collection.Collection(self.db, name, **kwargs)
        if settings.DEBUG:
            collection = CollectionDebugWrapper(collection)
        return collection

    @requires_connection
    def drop_database(self, name):
        return self._connection.drop_database(name)

    @requires_connection
    def collection_names(self):
        return self.db.collection_names()

    def _connect(self):
        host = self.settings_dict['HOST'] or None
        port = self.settings_dict.get('PORT', None) or None
        # If PORT is not specified it is set to '' which makes PyMongo fail.
        # Even if PyMongo sets the port to 27017 I think we should ensure it
        # is never '' (but None instead) and let PyMongo do the change.
        user = self.settings_dict.get('USER', None)
        password = self.settings_dict.get('PASSWORD')
        self.db_name = self.settings_dict['NAME']

        options = {
            'SAFE_INSERTS': False,
            'WAIT_FOR_SLAVES': 0,
            'SLAVE_OKAY': False,
        }

        options.update(self.settings_dict.get('OPTIONS', {}))

        for option in options.keys():
            if option in self.settings_dict:
                import warnings
                warnings.warn(
                    'for %s please use the OPTIONS dictionary' % option,
                    DeprecationWarning
                )

                options[option] = self.settings_dict[option]

        def complain_unless(condition, message):
            if not condition:
                raise ImproperlyConfigured(message)

        if host is not None:
            if pymongo.version >= '1.8':
                complain_unless(isinstance(host, (basestring, list)),
                    "If set, HOST must be a string or a list of strings")
            else:
                complain_unless(isinstance(host, basestring),
                    "If set, HOST must be a string")

        if port:
            try:
                port = int(port)
            except ValueError:
                raise ImproperlyConfigured("If set, PORT must be an integer"
                                           " (got %r instead)" % port)

        complain_unless(isinstance(options['SAFE_INSERTS'], bool),
            "If set, SAFE_INSERTS must be True or False")
        complain_unless(isinstance(options['SLAVE_OKAY'], bool),
            "If set, SLAVE_OKAY must be True or False")
        complain_unless(isinstance(options['WAIT_FOR_SLAVES'], int),
            "If set, WAIT_FOR_SLAVES must be an integer")

        self.safe_inserts = options['SAFE_INSERTS']
        self.wait_for_slaves = options['WAIT_FOR_SLAVES']
        slave_okay = options['SLAVE_OKAY']

        self._connection = pymongo.Connection(host=host, port=port, slave_okay=slave_okay)
        self.db = self._connection[self.db_name]
        if user and password:
            complain_unless(self.db.authenticate(user, password),
                            "Invalid username or password")
        self._add_serializer()
        self._connected = True
        connection_created.send(sender=self.__class__, connection=self)

    def _add_serializer(self):
        for option in ['MONGODB_AUTOMATIC_REFERENCING',
                       'MONGODB_ENGINE_ENABLE_MODEL_SERIALIZATION']:
            if getattr(settings, option, False):
                from .serializer import TransformDjango
                self.db.add_son_manipulator(TransformDjango())
                return
