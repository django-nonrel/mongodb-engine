import pymongo

from djangotoolbox.db.base import NonrelDatabaseFeatures, \
    NonrelDatabaseWrapper, NonrelDatabaseClient, \
    NonrelDatabaseValidation, NonrelDatabaseIntrospection

from django.core.exceptions import ImproperlyConfigured

from .creation import DatabaseCreation
from django_mongodb_engine.mongodb.operations import DatabaseOperations

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
    def __init__(self, *args, **kwds):
        super(DatabaseWrapper, self).__init__(*args, **kwds)
        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.validation = DatabaseValidation(self)
        self.introspection = DatabaseIntrospection(self)
        self._is_connected = False

    @property
    def db_connection(self):
        self._ensure_is_connected()
        return self._db_connection

    def _ensure_is_connected(self):
        if not self._is_connected:
            settings_dict = self.settings_dict
            try:
                PORT = int(settings_dict["PORT"])
            except ValueError:
                raise ImproperlyConfigured("PORT must be an integer")
            NAME = settings_dict["NAME"]
            HOST = settings_dict["HOST"]
            USER = settings_dict["USER"]
            PASSWORD = settings_dict["PASSWORD"]
            connection = pymongo.Connection(HOST, PORT, slave_okay=True)
            if USER and PASSWORD:
                auth = connection['admin'].authenticate(USER, PASSWORD)
                if not auth:
                    raise ImproperlyConfigured("Username and/or password for "
                                               "the MongoDB are not correct")
            from .mongodb_serializer import TransformDjango
            self._connection = connection
            self.db_name = NAME
            self._db_connection = connection[NAME]
            self._db_connection.add_son_manipulator(TransformDjango())
            self._is_connected = True
