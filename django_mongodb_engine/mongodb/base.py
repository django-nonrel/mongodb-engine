from django.core.exceptions import ImproperlyConfigured

import pymongo
from .creation import DatabaseCreation
from .operations import DatabaseOperations

from djangotoolbox.db.base import NonrelDatabaseFeatures, \
    NonrelDatabaseWrapper, NonrelDatabaseClient, \
    NonrelDatabaseValidation, NonrelDatabaseIntrospection
  
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
        self.w = 0
        self._is_connected = False

    @property
    def db_connection(self):
        self._ensure_is_connected()
        return self._db_connection

    def _ensure_is_connected(self):
        if not self._is_connected:
            host = self.settings_dict['HOST'] or None
            port = self.settings_dict['PORT'] or None
            safe = self.settings_dict.get('SAFE_INSERTS', False)
            wait = self.settings_dict.get('WAIT_FOR_SLAVES', 0)

            try:
                import warnings
                
                if pymongo.version >= '1.8':
                    assert host is None or isinstance(host, (basestring, list)), 'If set, HOST must be a string or a list of strings'
                else:
                    assert host is None or isinstance(host, basestring), 'If set, HOST must be a string'

                if isinstance(host, basestring) and host.startswith('mongodb://'):
                    if port:
                        warnings.warn("If the host is a mongodb:// URL, setting the port is useless. I'll ignore it", RuntimeWarning)
                    
                try:
                    port = int(port)
                except ValueError:
                    raise ImproperlyConfigured, 'If set, PORT must be an integer'

                assert isinstance(safe, bool), 'If set, SAFE_INSERTS must be True or False'
                assert isinstance(wait, int), 'If set, WAIT_FOR_SLAVES must be an integer'

            except AssertionError, e:
                raise ImproperlyConfigured(e)

            self.safe_inserts = safe
            self.w = wait
            
            user = self.settings_dict.get('USER', None)
            password = self.settings_dict.get('PASSWORD', None)

            slave_okay = self.settings_dict.get('SLAVE_OKAY', False) 

            self._connection = pymongo.Connection(host=host, port=port, slave_okay=slave_okay)
            
            self.db_name = self.settings_dict['NAME']
            
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
