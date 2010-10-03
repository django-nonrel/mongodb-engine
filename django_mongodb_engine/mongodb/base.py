import warnings

from django.core.exceptions import ImproperlyConfigured

import pymongo
from .creation import DatabaseCreation
from .operations import DatabaseOperations

from djangotoolbox.db.base import NonrelDatabaseFeatures, \
    NonrelDatabaseWrapper, NonrelDatabaseClient, \
    NonrelDatabaseValidation, NonrelDatabaseIntrospection

class ImproperlyConfiguredWarning(Warning):
    pass

class DatabaseFeatures(NonrelDatabaseFeatures):
    string_based_auto_field = True

class DatabaseClient(NonrelDatabaseClient):
    pass

class DatabaseValidation(NonrelDatabaseValidation):
    pass

class DatabaseIntrospection(NonrelDatabaseIntrospection):
    def table_names(self):
        """
        Show defined models
        """
        return self.connection.db_connection.collection_names()

    def sequence_list(self):
        # TODO: check if it's necessary to implement that
        pass

class DatabaseWrapper(NonrelDatabaseWrapper):
    def _cursor(self):
        self._ensure_is_connected()
        return self._connection

    def __init__(self, *args, **kwds):
        super(DatabaseWrapper, self).__init__(*args, **kwds)
        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.validation = DatabaseValidation(self)
        self.introspection = DatabaseIntrospection(self)
        self.safe_inserts = False
        self.wait_for_slaves = 0
        self._is_connected = False

    @property
    def db_connection(self):
        self._ensure_is_connected()
        return self._db_connection

    def _ensure_is_connected(self):
        if not self._is_connected:
            host = self.settings_dict['HOST'] or None
            port = self.settings_dict['PORT'] or None
            user = self.settings_dict.get('USER', None)
            password = self.settings_dict.get('PASSWORD')
            self.safe_inserts = self.settings_dict.get('SAFE_INSERTS', False)
            self.wait_for_slaves = self.settings_dict.get('WAIT_FOR_SLAVES', 0)
            slave_okay = self.settings_dict.get('SLAVE_OKAY', False)
            self.db_name = self.settings_dict['NAME']

            try:
                if host is not None:
                    if pymongo.version >= '1.8':
                        assert isinstance(host, (basestring, list)), \
                            'If set, HOST must be a string or a list of strings'
                    else:
                        assert isinstance(host, basestring), 'If set, HOST must be a string'

                if port:
                    if isinstance(host, basestring) and host.startswith('mongodb://'):
                        # If host starts with mongodb:// the port will be
                        # ignored so lets make sure it is None
                        port = None
                        warnings.warn(
                            "If 'HOST' is a mongodb:// URL, the 'PORT' setting "
                            "will be ignored", ImproperlyConfiguredWarning
                        )
                    else:
                        try:
                            port = int(port)
                        except ValueError:
                            raise ImproperlyConfigured('If set, PORT must be an integer')

                assert isinstance(self.safe_inserts, bool), 'If set, SAFE_INSERTS must be True or False'
                assert isinstance(self.wait_for_slaves, int), 'If set, WAIT_FOR_SLAVES must be an integer'
            except AssertionError, e:
                raise ImproperlyConfigured(e)

            self._connection = pymongo.Connection(host=host, port=port, slave_okay=slave_okay)

            if user and password:
                auth = self._connection[self.db_name].authenticate(user, password)
                if not auth:
                    raise ImproperlyConfigured("Username and/or password for "
                                               "the MongoDB are not correct")

            self._db_connection = self._connection[self.db_name]

            from .mongodb_serializer import TransformDjango
            self._db_connection.add_son_manipulator(TransformDjango())

            # We're done!
            self._is_connected = True
